// ORVANTA Plasma startup splash (shown while the desktop loads after login).
// The rendered ORVANTA wallpaper, darkened, with the wordmark and a spinner.
// KSplash sets `stage` as startup progresses; the splash fades in at stage 2.
// SPDX-License-Identifier: MIT
import QtQuick

Rectangle {
    id: root
    color: "#050f20"

    property int stage

    onStageChanged: {
        if (stage == 2) {
            fadeIn.running = true
        }
    }

    Image {
        anchors.fill: parent
        source: "file:///usr/share/wallpapers/Orvanta/contents/images/3840x2160.jpg"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        sourceSize.width: root.width
        sourceSize.height: root.height
    }

    Rectangle {
        anchors.fill: parent
        color: "#050f20"
        opacity: 0.55
    }

    Item {
        id: content
        anchors.fill: parent
        opacity: 0

        Image {
            id: wordmark
            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.round(parent.height * 0.42 - height / 2)
            source: "file:///usr/share/orvanta/branding/orvanta-wordmark.png"
            fillMode: Image.PreserveAspectFit
            height: Math.round(parent.height * 0.28)
            width: Math.round(height * 1120 / 660)
            sourceSize.width: width
            sourceSize.height: height
            smooth: true
        }

        Image {
            id: spinner
            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.round(parent.height * 0.72 - height / 2)
            source: "file:///usr/share/orvanta/branding/spinner.png"
            width: Math.round(Math.min(96, parent.height * 0.075))
            height: width
            sourceSize.width: width
            sourceSize.height: height
            smooth: true

            RotationAnimator on rotation {
                from: 0
                to: 360
                duration: 1200
                loops: Animation.Infinite
                running: content.opacity > 0
            }
        }
    }

    OpacityAnimator {
        id: fadeIn
        target: content
        from: 0
        to: 1
        duration: 400
        easing.type: Easing.InOutQuad
    }
}
