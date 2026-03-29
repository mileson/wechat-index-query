#!/usr/bin/env swift

import AppKit
import ApplicationServices
import Foundation

func fail(_ message: String) -> Never {
    let safe = message.replacingOccurrences(of: "\"", with: "\\\"")
    fputs("{\"ok\":false,\"error\":\"\(safe)\"}\n", stderr)
    exit(1)
}

guard CommandLine.arguments.count >= 4 else {
    fail("usage: paste_keyword_at.swift <x> <y> <keyword>")
}

guard let x = Double(CommandLine.arguments[1]), let y = Double(CommandLine.arguments[2]) else {
    fail("invalid coordinates")
}

let keyword = CommandLine.arguments[3]

func postMouseClick(at point: CGPoint) {
    if let move = CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: .left) {
        move.post(tap: .cghidEventTap)
    }
    usleep(120_000)
    if let down = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left) {
        down.post(tap: .cghidEventTap)
    }
    usleep(50_000)
    if let up = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left) {
        up.post(tap: .cghidEventTap)
    }
}

func postKey(keyCode: CGKeyCode, flags: CGEventFlags = []) {
    if let down = CGEvent(keyboardEventSource: nil, virtualKey: keyCode, keyDown: true) {
        down.flags = flags
        down.post(tap: .cghidEventTap)
    }
    usleep(35_000)
    if let up = CGEvent(keyboardEventSource: nil, virtualKey: keyCode, keyDown: false) {
        up.flags = flags
        up.post(tap: .cghidEventTap)
    }
}

let pasteboard = NSPasteboard.general
let oldValue = pasteboard.string(forType: .string) ?? ""
pasteboard.clearContents()
pasteboard.setString(keyword, forType: .string)

let point = CGPoint(x: x, y: y)
postMouseClick(at: point)
usleep(350_000)
postKey(keyCode: 0, flags: .maskCommand)
usleep(120_000)
postKey(keyCode: 9, flags: .maskCommand)
usleep(180_000)
postKey(keyCode: 36)

pasteboard.clearContents()
pasteboard.setString(oldValue, forType: .string)

print("{\"ok\":true,\"x\":\(Int(x)),\"y\":\(Int(y))}")
