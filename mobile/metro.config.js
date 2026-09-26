// Metro config for a project that consumes `@mokli/sdk` from `../packages/mokli-sdk`.
// The SDK is installed via `file:`, so React must always resolve from this app's node_modules.
const { getDefaultConfig } = require("expo/metro-config");
const path = require("path");

const projectRoot = __dirname;
const sdkRoot = path.resolve(projectRoot, "../packages/mokli-sdk");

const config = getDefaultConfig(projectRoot);
config.watchFolders = [sdkRoot];
config.resolver.nodeModulesPaths = [path.resolve(projectRoot, "node_modules")];
config.resolver.disableHierarchicalLookup = true;
config.resolver.extraNodeModules = {
  react: path.resolve(projectRoot, "node_modules/react"),
};

module.exports = config;
