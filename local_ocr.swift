import Foundation
import Vision

func emit(_ obj: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys]), let string = String(data: data, encoding: .utf8) { print(string) }
}
if CommandLine.arguments.count < 2 {
    emit(["available": true, "backend": "apple_vision", "lines": [], "issues": ["Expected one local image path"]]); exit(2)
}
let path = CommandLine.arguments[1]
if !FileManager.default.fileExists(atPath: path) {
    emit(["available": true, "backend": "apple_vision", "lines": [], "issues": ["Image does not exist"]]); exit(2)
}
do {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = CommandLine.arguments.dropFirst(2).contains("--language-correction")
    request.minimumTextHeight = 0.003
    let supported = try request.supportedRecognitionLanguages()
    let languages = ["zh-Hans", "en-US"].filter { supported.contains($0) }
    guard languages.contains("zh-Hans") else {
        emit(["available": false, "backend": "apple_vision", "lines": [], "issues": ["Simplified Chinese recognition is unavailable"], "supported_languages": supported]); exit(3)
    }
    request.recognitionLanguages = languages
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: path), options: [:])
    try handler.perform([request])
    var lines: [[String: Any]] = []
    for observation in request.results ?? [] {
        guard let candidate = observation.topCandidates(1).first else { continue }
        let box = observation.boundingBox
        lines.append(["text": candidate.string, "box": [Double(box.origin.x), Double(1.0-box.origin.y-box.height), Double(box.width), Double(box.height)], "confidence": Double(candidate.confidence)])
    }
    lines.sort { a, b in
        let aa = a["box"] as! [Double], bb = b["box"] as! [Double]
        return abs(aa[1]-bb[1]) > 0.008 ? aa[1] < bb[1] : aa[0] < bb[0]
    }
    var issues: [String] = []
    var rectangles: [[String: Any]] = []
    do {
        let rectangleRequest = VNDetectRectanglesRequest()
        rectangleRequest.maximumObservations = 100
        rectangleRequest.minimumSize = 0.03
        rectangleRequest.minimumConfidence = 0.5
        rectangleRequest.minimumAspectRatio = 0.15
        rectangleRequest.maximumAspectRatio = 1.0
        try handler.perform([rectangleRequest])
        for observation in rectangleRequest.results ?? [] {
            let b = observation.boundingBox
            let ratio = b.width / max(b.height, 0.00001)
            if ratio >= 0.15 && ratio <= 6.0 {
                rectangles.append(["box": [Double(b.origin.x), Double(1.0-b.origin.y-b.height), Double(b.width), Double(b.height)], "confidence": Double(observation.confidence)])
            }
        }
    } catch { issues.append("Rectangle detection failed: \(error.localizedDescription)") }

    if lines.isEmpty { issues.append("No text recognized; do not treat this as verified empty content") }
    emit(["available": true, "backend": "apple_vision", "lines": lines, "issues": issues, "languages": languages, "coordinate_origin": "top-left", "recognition_level": "accurate", "language_correction": request.usesLanguageCorrection, "rectangles": rectangles])
} catch {
    emit(["available": true, "backend": "apple_vision", "lines": [], "issues": ["Vision request failed: \(error.localizedDescription)"]]); exit(1)
}
