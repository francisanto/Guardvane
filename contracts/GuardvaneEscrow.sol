// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title GuardvaneEscrow
 * @notice Secure decentralized escrow for Guardvane + OpiHub marketplace.
 * Holds audit review fees in escrow between Customer and Specialist Provider.
 * Reentrancy protected, checks-effects-interactions, strict role boundaries.
 */
contract GuardvaneEscrow {
    enum EscrowState { Created, Funded, WorkInProgress, Submitted, Released, Disputed, Refunded, Cancelled }

    struct EscrowOrder {
        bytes32 orderIdHash;       // keccak256 hash of order_id string
        address payable customer;  // Order creator / payer
        address payable provider;  // Specialist security auditor
        uint256 amount;            // Escrow deposit in wei
        EscrowState state;         // Current escrow state
        uint256 fundedAt;
        uint256 releasedAt;
        string orderId;            // Plain order ID string for indexing
    }

    address public owner;
    bool private _locked; // Reentrancy guard

    mapping(bytes32 => EscrowOrder) public orders;
    mapping(string => bytes32) public orderIdToHash;

    event EscrowFunded(string indexed orderId, bytes32 indexed orderHash, address indexed customer, address provider, uint256 amount);
    event WorkStarted(string indexed orderId, bytes32 indexed orderHash);
    event DeliverableSubmitted(string indexed orderId, bytes32 indexed orderHash);
    event EscrowReleased(string indexed orderId, bytes32 indexed orderHash, address indexed provider, uint256 amount);
    event EscrowRefunded(string indexed orderId, bytes32 indexed orderHash, address indexed customer, uint256 amount);
    event EscrowDisputed(string indexed orderId, bytes32 indexed orderHash, address indexed disputeBy);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier nonReentrant() {
        require(!_locked, "ReentrancyGuard: reentrant call");
        _locked = true;
        _;
        _locked = false;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Deposit funds into escrow for a specific order.
     * @param orderId Unique marketplace order ID (e.g. ord_186a4b5f)
     * @param provider Specialist wallet address
     */
    function depositEscrow(string calldata orderId, address payable provider) external payable nonReentrant {
        require(msg.value > 0, "Deposit amount must be > 0");
        require(provider != address(0), "Invalid provider address");
        require(provider != msg.sender, "Customer cannot be provider");
        
        bytes32 orderHash = keccak256(abi.encodePacked(orderId));
        require(orders[orderHash].amount == 0, "Order escrow already exists");

        orders[orderHash] = EscrowOrder({
            orderIdHash: orderHash,
            customer: payable(msg.sender),
            provider: provider,
            amount: msg.value,
            state: EscrowState.Funded,
            fundedAt: block.timestamp,
            releasedAt: 0,
            orderId: orderId
        });
        orderIdToHash[orderId] = orderHash;

        emit EscrowFunded(orderId, orderHash, msg.sender, provider, msg.value);
    }

    /**
     * @notice Provider acknowledges start of work.
     */
    function startWork(string calldata orderId) external {
        bytes32 orderHash = keccak256(abi.encodePacked(orderId));
        EscrowOrder storage ord = orders[orderHash];
        require(ord.amount > 0, "Escrow not found");
        require(msg.sender == ord.provider, "Only assigned provider");
        require(ord.state == EscrowState.Funded, "Must be in Funded state");

        ord.state = EscrowState.WorkInProgress;
        emit WorkStarted(orderId, orderHash);
    }

    /**
     * @notice Provider submits deliverable / report.
     */
    function submitDeliverable(string calldata orderId) external {
        bytes32 orderHash = keccak256(abi.encodePacked(orderId));
        EscrowOrder storage ord = orders[orderHash];
        require(ord.amount > 0, "Escrow not found");
        require(msg.sender == ord.provider, "Only assigned provider");
        require(ord.state == EscrowState.Funded || ord.state == EscrowState.WorkInProgress, "Invalid state for submit");

        ord.state = EscrowState.Submitted;
        emit DeliverableSubmitted(orderId, orderHash);
    }

    /**
     * @notice Customer accepts report and releases escrow payment directly to provider.
     */
    function releaseEscrow(string calldata orderId) external nonReentrant {
        bytes32 orderHash = keccak256(abi.encodePacked(orderId));
        EscrowOrder storage ord = orders[orderHash];
        require(ord.amount > 0, "Escrow not found");
        require(msg.sender == ord.customer || msg.sender == owner, "Only customer or arbiter");
        require(
            ord.state == EscrowState.Funded || ord.state == EscrowState.WorkInProgress || ord.state == EscrowState.Submitted,
            "Cannot release in current state"
        );

        uint256 payout = ord.amount;
        ord.amount = 0; // State change before transfer (reentrancy prevention)
        ord.state = EscrowState.Released;
        ord.releasedAt = block.timestamp;

        (bool sent, ) = ord.provider.call{value: payout}("");
        require(sent, "Failed to send Ether to provider");

        emit EscrowReleased(orderId, orderHash, ord.provider, payout);
    }

    /**
     * @notice Refund escrow to customer (in case of rejection, cancellation, or dispute resolution).
     */
    function refundEscrow(string calldata orderId) external nonReentrant {
        bytes32 orderHash = keccak256(abi.encodePacked(orderId));
        EscrowOrder storage ord = orders[orderHash];
        require(ord.amount > 0, "Escrow not found");
        require(
            msg.sender == ord.provider || msg.sender == owner || (msg.sender == ord.customer && ord.state == EscrowState.Funded),
            "Unauthorized refund"
        );
        require(ord.state != EscrowState.Released, "Already released");

        uint256 refundAmount = ord.amount;
        ord.amount = 0;
        ord.state = EscrowState.Refunded;

        (bool sent, ) = ord.customer.call{value: refundAmount}("");
        require(sent, "Failed to refund Ether to customer");

        emit EscrowRefunded(orderId, orderHash, ord.customer, refundAmount);
    }

    /**
     * @notice Raise dispute on an escrow order.
     */
    function disputeEscrow(string calldata orderId) external {
        bytes32 orderHash = keccak256(abi.encodePacked(orderId));
        EscrowOrder storage ord = orders[orderHash];
        require(ord.amount > 0, "Escrow not found");
        require(msg.sender == ord.customer || msg.sender == ord.provider, "Only order parties");
        require(ord.state != EscrowState.Released && ord.state != EscrowState.Refunded, "Order finalized");

        ord.state = EscrowState.Disputed;
        emit EscrowDisputed(orderId, orderHash, msg.sender);
    }

    function getOrder(string calldata orderId) external view returns (
        address customer,
        address provider,
        uint256 amount,
        EscrowState state,
        uint256 fundedAt,
        uint256 releasedAt
    ) {
        bytes32 orderHash = keccak256(abi.encodePacked(orderId));
        EscrowOrder memory ord = orders[orderHash];
        return (ord.customer, ord.provider, ord.amount, ord.state, ord.fundedAt, ord.releasedAt);
    }
}

