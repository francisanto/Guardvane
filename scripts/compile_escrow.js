/**
 * Compiles GuardvaneEscrow.sol and outputs ABI and bytecode to contracts/artifacts.
 */

const fs = require('fs');
const path = require('path');
const solc = require('solc');

const contractPath = path.resolve(__dirname, '..', 'contracts', 'GuardvaneEscrow.sol');
const source = fs.readFileSync(contractPath, 'utf8');

const input = {
  language: 'Solidity',
  sources: {
    'GuardvaneEscrow.sol': {
      content: source
    }
  },
  settings: {
    optimizer: {
      enabled: true,
      runs: 200
    },
    outputSelection: {
      '*': {
        '*': ['abi', 'evm.bytecode']
      }
    }
  }
};

const output = JSON.parse(solc.compile(JSON.stringify(input)));

if (output.errors) {
  let hasError = false;
  for (const err of output.errors) {
    if (err.severity === 'error') {
      console.error(err.formattedMessage);
      hasError = true;
    } else {
      console.warn(err.formattedMessage);
    }
  }
  if (hasError) process.exit(1);
}

const contract = output.contracts['GuardvaneEscrow.sol']['GuardvaneEscrow'];
const artifactsDir = path.resolve(__dirname, '..', 'contracts', 'artifacts');
if (!fs.existsSync(artifactsDir)) {
  fs.mkdirSync(artifactsDir, { recursive: true });
}

const artifact = {
  contractName: 'GuardvaneEscrow',
  abi: contract.abi,
  bytecode: contract.evm.bytecode.object
};

fs.writeFileSync(
  path.join(artifactsDir, 'GuardvaneEscrow.json'),
  JSON.stringify(artifact, null, 2)
);

console.log('Contract compiled successfully!');
console.log('Artifacts written to:', path.join(artifactsDir, 'GuardvaneEscrow.json'));
console.log('Bytecode length:', artifact.bytecode.length);
console.log('ABI methods count:', artifact.abi.length);

