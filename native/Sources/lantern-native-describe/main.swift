// Real native image-input narration for lantern's NativeImageBackend.
//
// Deliberately a standalone compiled executable rather than a PyObjC bridge:
// FoundationModels' image-input surface (Attachment<ImageAttachmentContent>,
// Prompt, PromptRepresentable) is pure-Swift -- generics and protocols that
// PyObjC's Objective-C-runtime bridge cannot see at all (verified directly:
// `import FoundationModels` fails under PyObjC even with the beta installed).
// This binary is invoked via subprocess from lantern's Python code, the same
// pattern already used for /usr/sbin/screencapture in capture.py.
//
// Usage: lantern-native-describe <image-path>
// Reads session instructions from stdin (avoids ARG_MAX/shell-escaping
// issues with a long instructions string). Prints the narration to stdout
// on success. Non-zero exit + message on stderr on failure.

import Foundation
import FoundationModels

func fail(_ message: String, code: Int32) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(code)
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    fail("Usage: lantern-native-describe <image-path> (instructions read from stdin)", code: 2)
}
let imagePath = args[1]

let instructionsData = FileHandle.standardInput.readDataToEndOfFile()
guard let instructions = String(data: instructionsData, encoding: .utf8), !instructions.isEmpty else {
    fail("No instructions provided on stdin", code: 2)
}

let model = SystemLanguageModel.default
guard model.isAvailable else {
    fail("SystemLanguageModel unavailable: \(model.availability)", code: 3)
}

let imageURL = URL(fileURLWithPath: imagePath)
guard FileManager.default.fileExists(atPath: imagePath) else {
    fail("Image not found at \(imagePath)", code: 2)
}

let semaphore = DispatchSemaphore(value: 0)
var narration: String?
var failure: String?

Task {
    let attachment = FoundationModels.Attachment(imageURL: imageURL).label("photo")
    let session = LanguageModelSession(model: model, instructions: instructions)
    do {
        // Prompt's variadic initializer is @usableFromInline, not public --
        // only reachable through the @PromptBuilder closure form, which the
        // compiler expands via the public PromptBuilder.buildBlock.
        let response = try await session.respond {
            attachment
            "Describe what is shown."
        }
        narration = response.content
    } catch {
        failure = "Generation failed: \(error)"
    }
    semaphore.signal()
}

semaphore.wait()

if let failure {
    fail(failure, code: 4)
}
print(narration ?? "")
