#include <iostream>

#include "ofxCore.h"
#include "ofxImageEffect.h"
#include "ofxProperty.h"


static bool g_advertisePlugin = true;
static OfxHost* g_host = nullptr;

static void test_plugin_setHost(OfxHost* host) {
	std::cout << __FUNCTION__ << "(" << host << ")\n";
	g_host = host;
}

OfxStatus test_plugin_mainEntry(const char* action, const void* handle, OfxPropertySetHandle inArgs, OfxPropertySetHandle outArgs) {
	std::cout << __FUNCTION__ << "(" << action << ", " << handle << ", " << inArgs << ", " << outArgs << ")\n";
	return kOfxStatErrUnsupported;
}

static OfxPlugin kTestPluginInfo = {
	kOfxImageEffectPluginApi, /* pluginApi */
	1, /* apiVersion */
	"org.ajc.test_plugin", /* pluginIdentifier */
	1, /* pluginVersionMajor */
	0, /* pluginVersionMinor */
	test_plugin_setHost,
	test_plugin_mainEntry,
};

OfxExport OfxStatus OfxSetHost(const OfxHost* host) {
	std::cout << __FUNCTION__ << "(" << host << ")\n";
	return kOfxStatOK;
}

OfxExport int OfxGetNumberOfPlugins(void) {
	std::cout << __FUNCTION__ << "()\n";
	return g_advertisePlugin ? 1 : 0;
}

OfxExport OfxPlugin* OfxGetPlugin(int nth) {
	std::cout << __FUNCTION__ << "(" << nth << ")\n";
	return (g_advertisePlugin && nth == 0) ? &kTestPluginInfo : nullptr;
}

