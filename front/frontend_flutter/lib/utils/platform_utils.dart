// platform_utils.dart
import 'platform_utils_stub.dart' 
    if (dart.library.html) 'platform_utils_web.dart' as impl;

class PlatformUtils {
  static Map<String, dynamic>? getUrlInfo() {
    return impl.getUrlInfo();
  }
}
