#include "third_party/ofxhBinaryStrict.h"
#include "ofxhPluginCache.h"

typedef  int (*GetNumberOfPluginsFunc)();
typedef  OfxPlugin* (*GetPluginFunc)(int);

int main(int argc, const char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <plugin>\n";
        return 1;
    }

    const char* const binaryPath = argv[1];

    OFX::BinaryStrict bin(binaryPath);

    if (bin.isInvalid()) {
        std::cerr << "error: '" << binaryPath << "' is invalid.\n";
        return 1;
    }

    bin.load();

    if (!bin.isLoaded()) {
        std::cerr << "error: '" << binaryPath << "' failed to load.\n";
        return 1;
    }

    auto* getNumberOfPlugins = reinterpret_cast<GetNumberOfPluginsFunc>(bin.findSymbol("OfxGetNumberOfPlugins"));
    auto* getPluginFunc = reinterpret_cast<GetPluginFunc>(bin.findSymbol("OfxGetPlugin"));

    if (getNumberOfPlugins == nullptr || getPluginFunc == nullptr) {
        std::cerr << "error: '" << binaryPath << "' missing required symbols.\n";
        return 1;
    }

    const int numPlugins = getNumberOfPlugins();

    std::cout << "numPlugins: " << numPlugins << "\n";

    if (numPlugins <= 0) {
        std::cerr << "error: unexpected number of plugins.\n";
        return 1;
    }

    for (int i = 0; i < numPlugins; ++i) {
        auto* plugin = getPluginFunc(i);
        if (plugin == nullptr) {
            std::cerr << "Failed to get plugin " << i << "\n";
            return 1;
        }

        std::cout << "plugin[" << i << "] : " << plugin->pluginIdentifier << " v" << plugin->pluginVersionMajor << "." << plugin->pluginVersionMinor << "\n";
    }

    return 0;
}