import 'package:flutter/material.dart';

/// Tipos de dispositivos según el tamaño de pantalla
enum DeviceType {
  mobile,
  tablet,
  desktop,
}

/// Información de responsive para construir interfaces adaptativas
class ResponsiveInfo {
  final Size screenSize;
  final DeviceType deviceType;
  final bool isMobile;
  final bool isTablet;
  final bool isDesktop;
  final bool isSmallDevice;
  final bool isLandscape;
  final double padding;
  final double cardPadding;
  final double spacing;
  final double borderRadius;
  final double smallBorderRadius;
  final double iconPadding;
  final double listTilePadding;
  final double listTileIconSize;
  final bool showDescriptions;
  final bool showSecondaryInfo;
  final ResponsiveFontSizes fontSize;
  final double safeAreaBottom;
  final double safeAreaTop;

  ResponsiveInfo({
    required this.screenSize,
    required this.deviceType,
    required this.isMobile,
    required this.isTablet,
    required this.isDesktop,
    required this.isSmallDevice,
    required this.isLandscape,
    required this.padding,
    required this.cardPadding,
    required this.spacing,
    required this.borderRadius,
    required this.smallBorderRadius,
    required this.iconPadding,
    required this.listTilePadding,
    required this.listTileIconSize,
    required this.showDescriptions,
    required this.showSecondaryInfo,
    required this.fontSize,
    required this.safeAreaBottom,
    required this.safeAreaTop,
  });

  /// Obtiene el número de columnas para un grid basado en el tipo de dispositivo
  int getGridCrossAxisCount({int maxColumns = 4, int minColumns = 1}) {
    if (isMobile) return minColumns;
    if (isTablet) return (maxColumns * 0.66).round().clamp(minColumns, maxColumns);
    return maxColumns;
  }

  /// Obtiene el aspect ratio para cards en un grid
  double getGridAspectRatio({double mobileRatio = 1.5, double tabletRatio = 1.3, double desktopRatio = 1.2}) {
    if (isSmallDevice) return mobileRatio * 1.2;
    if (isMobile) return mobileRatio;
    if (isTablet) return tabletRatio;
    return desktopRatio;
  }

  /// Calcula el ancho de un elemento en un layout tipo grid
  double calculateItemWidth(double parentWidth, int columns) {
    return (parentWidth - (columns - 1) * spacing) / columns;
  }
}

/// Tamaños de fuente responsive
class ResponsiveFontSizes {
  final double header;
  final double title;
  final double sectionTitle;
  final double subtitle;
  final double body;
  final double caption;
  final double button;
  final double icon;
  final double smallIcon;
  final double largeIcon;
  final double statValue;
  final double emptyStateIcon;

  ResponsiveFontSizes({
    required this.header,
    required this.title,
    required this.sectionTitle,
    required this.subtitle,
    required this.body,
    required this.caption,
    required this.button,
    required this.icon,
    required this.smallIcon,
    required this.largeIcon,
    required this.statValue,
    required this.emptyStateIcon,
  });
}

/// Widget builder que proporciona información responsive
class ResponsiveBuilder extends StatelessWidget {
  final Widget Function(BuildContext context, ResponsiveInfo sizingInfo) builder;

  const ResponsiveBuilder({
    super.key,
    required this.builder,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final mediaQuery = MediaQuery.of(context);
        final sizingInfo = _calculateResponsiveInfo(mediaQuery, constraints);
        return builder(context, sizingInfo);
      },
    );
  }

  static ResponsiveInfo _calculateResponsiveInfo(MediaQueryData mediaQuery, BoxConstraints constraints) {
    final screenSize = mediaQuery.size;
    final width = screenSize.width;
    final height = screenSize.height;
    final orientation = mediaQuery.orientation;
    
    // Determinar tipo de dispositivo
    DeviceType deviceType;
    final isMobile = width < 600;
    final isTablet = width >= 600 && width < 900;
    final isDesktop = width >= 900;
    
    if (isMobile) {
      deviceType = DeviceType.mobile;
    } else if (isTablet) {
      deviceType = DeviceType.tablet;
    } else {
      deviceType = DeviceType.desktop;
    }
    
    // Detectar características especiales
    final isSmallDevice = height < 600 || (isMobile && height < 700);
    final isLandscape = orientation == Orientation.landscape;
    
    // Calcular valores de spacing y padding
    double padding;
    double cardPadding;
    double spacing;
    double borderRadius;
    double iconPadding;
    double listTilePadding;
    
    if (isSmallDevice) {
      padding = 12.0;
      cardPadding = 10.0;
      spacing = 6.0;
      borderRadius = 12.0;
      iconPadding = 6.0;
      listTilePadding = 4.0;
    } else if (isMobile) {
      padding = 16.0;
      cardPadding = 14.0;
      spacing = 10.0;
      borderRadius = 16.0;
      iconPadding = 8.0;
      listTilePadding = 6.0;
    } else if (isTablet) {
      padding = 24.0;
      cardPadding = 18.0;
      spacing = 14.0;
      borderRadius = 20.0;
      iconPadding = 10.0;
      listTilePadding = 8.0;
    } else {
      padding = 32.0;
      cardPadding = 24.0;
      spacing = 18.0;
      borderRadius = 24.0;
      iconPadding = 12.0;
      listTilePadding = 10.0;
    }
    
    // Ajustar para landscape en móviles
    if (isMobile && isLandscape) {
      padding *= 0.8;
      cardPadding *= 0.8;
      spacing *= 0.8;
    }
    
    // Tamaños de fuente responsive
    ResponsiveFontSizes fontSize;
    if (isSmallDevice) {
      fontSize = ResponsiveFontSizes(
        header: 18,
        title: 16,
        sectionTitle: 14,
        subtitle: 12,
        body: 11,
        caption: 9,
        button: 11,
        icon: 16,
        smallIcon: 12,
        largeIcon: 28,
        statValue: 18,
        emptyStateIcon: 36,
      );
    } else if (isMobile) {
      fontSize = ResponsiveFontSizes(
        header: 26,
        title: 20,
        sectionTitle: 17,
        subtitle: 14,
        body: 13,
        caption: 11,
        button: 12,
        icon: 20,
        smallIcon: 14,
        largeIcon: 34,
        statValue: 22,
        emptyStateIcon: 44,
      );
    } else if (isTablet) {
      fontSize = ResponsiveFontSizes(
        header: 30,
        title: 24,
        sectionTitle: 20,
        subtitle: 16,
        body: 14,
        caption: 12,
        button: 13,
        icon: 22,
        smallIcon: 16,
        largeIcon: 38,
        statValue: 26,
        emptyStateIcon: 52,
      );
    } else {
      fontSize = ResponsiveFontSizes(
        header: 34,
        title: 26,
        sectionTitle: 22,
        subtitle: 17,
        body: 15,
        caption: 13,
        button: 14,
        icon: 24,
        smallIcon: 18,
        largeIcon: 42,
        statValue: 30,
        emptyStateIcon: 60,
      );
    }
    
    return ResponsiveInfo(
      screenSize: screenSize,
      deviceType: deviceType,
      isMobile: isMobile,
      isTablet: isTablet,
      isDesktop: isDesktop,
      isSmallDevice: isSmallDevice,
      isLandscape: isLandscape,
      padding: padding,
      cardPadding: cardPadding,
      spacing: spacing,
      borderRadius: borderRadius,
      smallBorderRadius: borderRadius * 0.75,
      iconPadding: iconPadding,
      listTilePadding: listTilePadding,
      listTileIconSize: fontSize.icon * 1.8,
      showDescriptions: !isSmallDevice && !(isMobile && isLandscape),
      showSecondaryInfo: !isSmallDevice,
      fontSize: fontSize,
      safeAreaBottom: mediaQuery.padding.bottom,
      safeAreaTop: mediaQuery.padding.top,
    );
  }

  /// Método estático para obtener ResponsiveInfo sin necesidad de un widget
  static ResponsiveInfo of(BuildContext context) {
    final mediaQuery = MediaQuery.of(context);
    return _calculateResponsiveInfo(
      mediaQuery, 
      BoxConstraints(
        maxWidth: mediaQuery.size.width,
        maxHeight: mediaQuery.size.height,
      ),
    );
  }
}

/// Extensiones útiles para trabajar con responsive
extension ResponsiveExtensions on BuildContext {
  /// Obtiene la información responsive del contexto actual
  ResponsiveInfo get responsive => ResponsiveBuilder.of(this);
  
  /// Shortcuts para verificar el tipo de dispositivo
  bool get isMobile => responsive.isMobile;
  bool get isTablet => responsive.isTablet;
  bool get isDesktop => responsive.isDesktop;
  bool get isSmallDevice => responsive.isSmallDevice;
}

/// Widget que aplica padding responsive automáticamente
class ResponsivePadding extends StatelessWidget {
  final Widget child;
  final double? horizontal;
  final double? vertical;
  final double? all;
  final double multiplier;

  const ResponsivePadding({
    super.key,
    required this.child,
    this.horizontal,
    this.vertical,
    this.all,
    this.multiplier = 1.0,
  });

  @override
  Widget build(BuildContext context) {
    final info = context.responsive;
    
    if (all != null) {
      return Padding(
        padding: EdgeInsets.all(all! * multiplier),
        child: child,
      );
    }
    
    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: (horizontal ?? info.padding) * multiplier,
        vertical: (vertical ?? info.padding) * multiplier,
      ),
      child: child,
    );
  }
}

/// Widget contenedor responsive con decoración predefinida
class ResponsiveCard extends StatelessWidget {
  final Widget child;
  final Color? color;
  final double? elevation;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;

  const ResponsiveCard({
    super.key,
    required this.child,
    this.color,
    this.elevation,
    this.padding,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final info = context.responsive;
    
    final card = Container(
      padding: padding ?? EdgeInsets.all(info.cardPadding),
      decoration: BoxDecoration(
        color: color ?? Colors.white,
        borderRadius: BorderRadius.circular(info.borderRadius),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(elevation ?? 0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: child,
    );
    
    if (onTap != null) {
      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(info.borderRadius),
          child: card,
        ),
      );
    }
    
    return card;
  }
}

/// Grid responsive que se adapta automáticamente
class ResponsiveGrid extends StatelessWidget {
  final List<Widget> children;
  final int? crossAxisCount;
  final double? childAspectRatio;
  final double? crossAxisSpacing;
  final double? mainAxisSpacing;
  final int maxColumns;

  const ResponsiveGrid({
    super.key,
    required this.children,
    this.crossAxisCount,
    this.childAspectRatio,
    this.crossAxisSpacing,
    this.mainAxisSpacing,
    this.maxColumns = 4,
  });

  @override
  Widget build(BuildContext context) {
    final info = context.responsive;
    final columns = crossAxisCount ?? info.getGridCrossAxisCount(maxColumns: maxColumns);
    
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: columns,
        childAspectRatio: childAspectRatio ?? info.getGridAspectRatio(),
        crossAxisSpacing: crossAxisSpacing ?? info.spacing,
        mainAxisSpacing: mainAxisSpacing ?? info.spacing,
      ),
      itemCount: children.length,
      itemBuilder: (context, index) => children[index],
    );
  }
}

/// Espaciador responsive
class ResponsiveSpace extends StatelessWidget {
  final double multiplier;
  final bool isHorizontal;

  const ResponsiveSpace({
    super.key,
    this.multiplier = 1.0,
    this.isHorizontal = false,
  });

  @override
  Widget build(BuildContext context) {
    final spacing = context.responsive.spacing * multiplier;
    return isHorizontal 
        ? SizedBox(width: spacing)
        : SizedBox(height: spacing);
  }
}
