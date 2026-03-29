#!/usr/bin/env swift

import ApplicationServices
import Foundation

func fail(_ message: String) -> Never {
    let safe = message.replacingOccurrences(of: "\"", with: "\\\"")
    fputs("{\"ok\":false,\"error\":\"\(safe)\"}\n", stderr)
    exit(1)
}

guard CommandLine.arguments.count >= 3 else {
    fail("usage: click_at.swift <x> <y>")
}

guard let x = Double(CommandLine.arguments[1]), let y = Double(CommandLine.arguments[2]) else {
    fail("invalid coordinates")
}

let point = CGPoint(x: x, y: y)

if let move = CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: .left) {
    move.post(tap: .cghidEventTap)
}
usleep(100_000)
if let down = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left) {
    down.post(tap: .cghidEventTap)
}
usleep(50_000)
if let up = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left) {
    up.post(tap: .cghidEventTap)
}

print("{\"ok\":true,\"x\":\(Int(x)),\"y\":\(Int(y))}")
