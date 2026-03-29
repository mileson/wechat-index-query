#!/usr/bin/env swift

import AppKit
import Foundation
import Vision

struct RectPayload: Codable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

struct LinePayload: Codable {
    let text: String
    let confidence: Double
    let boundingBox: RectPayload
}

struct ResultPayload: Codable {
    let ok: Bool
    let image: String
    let lineCount: Int
    let fullText: String
    let lines: [LinePayload]
    let error: String?
}

func makeResult(ok: Bool, image: String, lines: [LinePayload], error: String?) -> ResultPayload {
    ResultPayload(
        ok: ok,
        image: image,
        lineCount: lines.count,
        fullText: lines.map(\.text).joined(separator: "\n"),
        lines: lines,
        error: error
    )
}

func printJSON(_ result: ResultPayload, exitCode: Int32 = 0) -> Never {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
    if let data = try? encoder.encode(result), let text = String(data: data, encoding: .utf8) {
        print(text)
    } else {
        print("{\"ok\":false,\"error\":\"failed to encode OCR result\"}")
    }
    exit(exitCode)
}

guard CommandLine.arguments.count >= 2 else {
    printJSON(
        makeResult(
            ok: false,
            image: "",
            lines: [],
            error: "usage: ocr_image.swift <image_path>"
        ),
        exitCode: 1
    )
}

let imagePath = CommandLine.arguments[1]
let imageURL = URL(fileURLWithPath: imagePath)

guard let image = NSImage(contentsOf: imageURL) else {
    printJSON(
        makeResult(
            ok: false,
            image: imagePath,
            lines: [],
            error: "failed to open image"
        ),
        exitCode: 1
    )
}

var rect = NSRect(origin: .zero, size: image.size)
guard let cgImage = image.cgImage(forProposedRect: &rect, context: nil, hints: nil) else {
    printJSON(
        makeResult(
            ok: false,
            image: imagePath,
            lines: [],
            error: "failed to create CGImage"
        ),
        exitCode: 1
    )
}

var capturedError: String?
var capturedLines: [LinePayload] = []

let request = VNRecognizeTextRequest { request, error in
    if let error {
        capturedError = error.localizedDescription
        return
    }

    let observations = (request.results as? [VNRecognizedTextObservation]) ?? []
    let sortedObservations = observations.sorted { lhs, rhs in
        if abs(lhs.boundingBox.midY - rhs.boundingBox.midY) > 0.02 {
            return lhs.boundingBox.midY > rhs.boundingBox.midY
        }
        return lhs.boundingBox.minX < rhs.boundingBox.minX
    }

    capturedLines = sortedObservations.compactMap { observation in
        guard let candidate = observation.topCandidates(1).first else {
            return nil
        }
        return LinePayload(
            text: candidate.string,
            confidence: Double(candidate.confidence),
            boundingBox: RectPayload(
                x: Double(observation.boundingBox.origin.x),
                y: Double(observation.boundingBox.origin.y),
                width: Double(observation.boundingBox.size.width),
                height: Double(observation.boundingBox.size.height)
            )
        )
    }
}

request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.minimumTextHeight = 0.015

do {
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try handler.perform([request])
} catch {
    capturedError = error.localizedDescription
}

if let capturedError {
    printJSON(
        makeResult(
            ok: false,
            image: imagePath,
            lines: [],
            error: capturedError
        ),
        exitCode: 1
    )
}

printJSON(
    makeResult(
        ok: true,
        image: imagePath,
        lines: capturedLines,
        error: nil
    )
)
