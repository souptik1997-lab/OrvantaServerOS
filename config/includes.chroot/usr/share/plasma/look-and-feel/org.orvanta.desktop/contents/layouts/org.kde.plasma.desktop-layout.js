// ORVANTA default desktop layout: KDE's default panel, image wallpaper plugin
// (the image itself comes from [Wallpaper] in ../defaults).
loadTemplate("org.kde.plasma.desktop.defaultPanel")

var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    desktopsArray[j].wallpaperPlugin = 'org.kde.image';
}
