import Quickshell
import Quickshell.Io
import QtQuick

// Kyuma Phase 15 overlay: top bar showing live voice-loop status.
// The harness loop writes /tmp/kyuma-state.json as
// {listening, last_sentence, last_action, result, ts}; this polls it
// every 500ms. Missing/corrupt file keeps the last known values.
ShellRoot {
  id: root
  property bool listening: false
  property string lastSentence: ""
  property string lastAction: ""
  property string lastResult: ""

  function applyState(text: string): void {
    var s;
    try {
      s = JSON.parse(text);
    } catch (e) {
      return;
    }
    if (typeof s !== "object" || s === null)
      return;
    root.listening = !!s.listening;
    root.lastSentence = s.last_sentence || "";
    root.lastAction = s.last_action || "";
    var r = s.result;
    if (typeof r === "string")
      root.lastResult = r;
    else if (typeof r === "object" && r !== null)
      root.lastResult = (r.code !== undefined ? r.code + " " : "") + (r.detail || "");
    else
      root.lastResult = "";
  }

  FileView {
    id: stateFile
    path: "/tmp/kyuma-state.json"
    watchChanges: true
    printErrors: false
    onLoaded: root.applyState(stateFile.text())
  }

  Timer {
    interval: 500
    running: true
    repeat: true
    onTriggered: stateFile.reload()
  }

  PanelWindow {
    anchors {
      top: true
      left: true
      right: true
    }
    implicitHeight: 32

    Rectangle {
      anchors.fill: parent
      color: root.listening ? "#1a3a2a" : "#141414"
      opacity: 0.92

      Row {
        anchors {
          verticalCenter: parent.verticalCenter
          left: parent.left
          leftMargin: 12
        }
        spacing: 18

        Text {
          text: root.listening ? "● LISTENING" : "○ idle"
          color: root.listening ? "#7dffa8" : "#888888"
        }
        Text {
          text: root.lastSentence
          color: "#ffffff"
          elide: Text.ElideRight
          width: Math.min(implicitWidth, 420)
        }
        Text {
          text: root.lastAction
          color: "#8ab4ff"
        }
        Text {
          text: root.lastResult
          color: "#cccccc"
          elide: Text.ElideRight
          width: Math.min(implicitWidth, 420)
        }
      }
    }
  }
}
