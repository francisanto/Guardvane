/**
 * Deployment script for GuardvaneEscrow on Rabdi Testnet (Chain ID 7794095).
 * Only broadcasts when explicitly called with --broadcast.
 */

const fs = require('fs');
const path = require('path');
const { ethers } = require('ethers');
require('dotenv').config({ path: path.resolve(__dirname, '..', '.env') });

async function main() {
  const rpcUrl = process.env.ARKIV_RPC_URL || 'https://rpc.rabdi.db-chain.testnet.arkiv.network';
  const privateKey = process.env.ARKIV_SIGNER_PRIVATE_KEY;
  const chainId = parseInt(process.env.ARKIV_CHAIN_ID || '7794095', 10);

  if (!privateKey) {
    console.error('Error: ARKIV_SIGNER_PRIVATE_KEY is not defined in .env');
    process.exit(1);
  }

  const artifactPath = path.resolve(__dirname, '..', 'contracts', 'artifacts', 'GuardvaneEscrow.json');
  if (!fs.existsSync(artifactPath)) {
    console.error('Error: GuardvaneEscrow.json not found. Run scripts/compile_escrow.js first.');
    process.exit(1);
  }

  const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const wallet = new ethers.Wallet(privateKey, provider);

  console.log('--- Guardvane Escrow Deployment ---');
  console.log('Network:', rpcUrl);
  console.log('Chain ID:', chainId);
  console.log('Deployer Wallet:', wallet.address);

  const balance = await provider.getBalance(wallet.address);
  console.log('Deployer Balance:', ethers.formatEther(balance), 'ETH / tGLM');

  const args = process.argv.slice(2);
  const shouldBroadcast = args.includes('--broadcast');

  if (!shouldBroadcast) {
    console.log('\n[DRY RUN] Transaction not broadcast. To deploy to Rabdi Testnet, pass --broadcast.');
    return;
  }

  console.log('\nDeploying GuardvaneEscrow contract...');
  const factory = new ethers.ContractFactory(artifact.abi, '0x' + artifact.bytecode, wallet);
  const contract = await factory.deploy();
  await contract.waitForDeployment();

  const contractAddress = await contract.getAddress();
  console.log('\n=============================================');
  console.log('GuardvaneEscrow Deployed Successfully!');
  console.log('Contract Address:', contractAddress);
  console.log('Explorer URL:', `https://explorer.rabdi.db-chain.testnet.arkiv.network/address/${contractAddress}`);
  console.log('=============================================\n');

  console.log('Add this address to your .env file:');
  console.log(`ESCROW_CONTRACT_ADDRESS=${contractAddress}`);
}

main().catch((err) => {
  console.error('Deployment failed:', err);
  process.exit(1);
});

