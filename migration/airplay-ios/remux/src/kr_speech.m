// kr_speech (ISSUE-347, owner: "match subtitle check needs to be added"): Apple's speech recognition on a stretch of
// the video's sound, iPhone build only, so subtitles can be checked against the words actually spoken (right film,
// right dub, right timing). The recognition runs on the phone only (requiresOnDeviceRecognition): the sound is never
// sent to Apple's servers, and a language the phone cannot recognise on its own is reported as not available.
// Pattern from Apple's documentation for SFSpeechRecognizer / SFSpeechAudioBufferRecognitionRequest: ask for
// authorization (the app's Info.plist carries NSSpeechRecognitionUsageDescription), append PCM buffers, endAudio, and
// read bestTranscription.segments (substring, timestamp, duration) from the final result.
#import <Foundation/Foundation.h>
#import <AVFoundation/AVFoundation.h>
#import <Speech/Speech.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "kr_speech.h"

static const char *auth_name(SFSpeechRecognizerAuthorizationStatus s) {
    switch (s) {
        case SFSpeechRecognizerAuthorizationStatusAuthorized: return "authorized";
        case SFSpeechRecognizerAuthorizationStatusDenied: return "denied";
        case SFSpeechRecognizerAuthorizationStatusRestricted: return "restricted";
        default: return "not_determined";
    }
}
static int put(char *json, int size, NSString *text) {
    const char *u = text.UTF8String; int n = (int)strlen(u);
    if (!json || size <= n) return -2;
    memcpy(json, u, (size_t)n + 1); return n;
}
static NSString *quoted(NSString *s) {
    NSData *d = [NSJSONSerialization dataWithJSONObject:@[s ?: @""] options:0 error:nil];
    NSString *a = d ? [[NSString alloc] initWithData:d encoding:NSUTF8StringEncoding] : @"[\"\"]";
    return [a substringWithRange:NSMakeRange(1, a.length - 2)];
}
static SFSpeechRecognizer *recognizer(const char *locale) {
    NSString *name = locale && *locale ? @(locale) : @"en-US";
    SFSpeechRecognizer *r = [[SFSpeechRecognizer alloc] initWithLocale:[NSLocale localeWithLocaleIdentifier:name]];
    if (r) { NSOperationQueue *q = [NSOperationQueue new]; q.maxConcurrentOperationCount = 1; r.queue = q; }   // never Kodi's main queue
    return r;
}

// {"auth":..., "available":bool, "on_device":bool}. Length, or negative.
__attribute__((visibility("default"))) int kodi_speech_state(const char *locale, char *json, int size) {
    @autoreleasepool {
        SFSpeechRecognizer *r = recognizer(locale);
        return put(json, size, [NSString stringWithFormat:@"{\"auth\":\"%s\",\"available\":%s,\"on_device\":%s}",
                                auth_name(SFSpeechRecognizer.authorizationStatus), r && r.isAvailable ? "true" : "false",
                                r && r.supportsOnDeviceRecognition ? "true" : "false"]);
    }
}
// Asks once (the system shows its own question); waits up to `seconds` for the answer. 1 authorized, 0 not.
__attribute__((visibility("default"))) int kodi_speech_authorize(double seconds) {
    if (SFSpeechRecognizer.authorizationStatus == SFSpeechRecognizerAuthorizationStatusNotDetermined) {
        dispatch_semaphore_t done = dispatch_semaphore_create(0);
        [SFSpeechRecognizer requestAuthorization:^(SFSpeechRecognizerAuthorizationStatus status) { dispatch_semaphore_signal(done); }];
        dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, (int64_t)(fmax(1, seconds) * NSEC_PER_SEC)));
    }
    return SFSpeechRecognizer.authorizationStatus == SFSpeechRecognizerAuthorizationStatusAuthorized;
}
// The words spoken from `start` for up to `seconds` (at most 60) of audio track `audio` (-1: the default), reading at
// most max_bytes of the file. JSON: {"status":"ok","from":s,"to":s,"words":[{"w":"...","t":s,"d":s},...]} with times
// on the video's clock, or {"status":"denied"|"not_on_device"|"unavailable"|"no_sound"|"failed","why":"..."}.
// Blocks the calling thread (never call it on Kodi's main thread). Length, or negative when json is too small.
__attribute__((visibility("default"))) int kodi_speech_words(const char *url, int audio, double start, double seconds,
                                                            long long max_bytes, const char *locale, char *json, int size) {
    @autoreleasepool {
        if (SFSpeechRecognizer.authorizationStatus != SFSpeechRecognizerAuthorizationStatusAuthorized)
            return put(json, size, [NSString stringWithFormat:@"{\"status\":\"denied\",\"why\":\"%s\"}", auth_name(SFSpeechRecognizer.authorizationStatus)]);
        SFSpeechRecognizer *r = recognizer(locale);
        if (!r || !r.isAvailable) return put(json, size, @"{\"status\":\"unavailable\",\"why\":\"no recognizer for this language\"}");
        if (!r.supportsOnDeviceRecognition) return put(json, size, @"{\"status\":\"not_on_device\",\"why\":\"this iPhone cannot recognise this language by itself\"}");
        int16_t *pcm = NULL; int n = 0; double first = 0; char err[256] = "";
        if (kr_speech_pcm(url, audio, start, fmin(seconds, 60), (int64_t)max_bytes, &pcm, &n, &first, err, sizeof err) < 0)
            return put(json, size, [NSString stringWithFormat:@"{\"status\":\"no_sound\",\"why\":%@}", quoted(@(err))]);
        AVAudioFormat *format = [[AVAudioFormat alloc] initWithCommonFormat:AVAudioPCMFormatFloat32 sampleRate:KR_SPEECH_RATE channels:1 interleaved:NO];
        AVAudioPCMBuffer *buffer = [[AVAudioPCMBuffer alloc] initWithPCMFormat:format frameCapacity:(AVAudioFrameCount)n];
        if (!buffer) { free(pcm); return put(json, size, @"{\"status\":\"failed\",\"why\":\"out of memory\"}"); }
        float *dst = buffer.floatChannelData[0];
        for (int i = 0; i < n; i++) dst[i] = pcm[i] / 32768.0f;
        buffer.frameLength = (AVAudioFrameCount)n; free(pcm);
        SFSpeechAudioBufferRecognitionRequest *request = [SFSpeechAudioBufferRecognitionRequest new];
        request.requiresOnDeviceRecognition = YES;
        request.shouldReportPartialResults = NO;
        request.taskHint = SFSpeechRecognitionTaskHintDictation;
        if (@available(iOS 16.0, *)) request.addsPunctuation = NO;
        [request appendAudioPCMBuffer:buffer];
        [request endAudio];
        __block SFSpeechRecognitionResult *final = nil; __block NSError *failure = nil;
        dispatch_semaphore_t done = dispatch_semaphore_create(0);
        SFSpeechRecognitionTask *task = [r recognitionTaskWithRequest:request resultHandler:^(SFSpeechRecognitionResult *result, NSError *error) {
            if (result.isFinal) final = result;
            if (error) failure = error;
            if (result.isFinal || error) dispatch_semaphore_signal(done);
        }];
        double length = (double)n / KR_SPEECH_RATE;
        if (dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, (int64_t)((length * 2 + 30) * NSEC_PER_SEC)))) {
            [task cancel];
            return put(json, size, @"{\"status\":\"failed\",\"why\":\"recognition took too long\"}");
        }
        if (!final) return put(json, size, [NSString stringWithFormat:@"{\"status\":\"failed\",\"why\":%@}", quoted(failure.localizedDescription)]);
        NSMutableString *out = [NSMutableString stringWithFormat:@"{\"status\":\"ok\",\"from\":%.3f,\"to\":%.3f,\"words\":[", first, first + length];
        BOOL comma = NO;
        for (SFTranscriptionSegment *s in final.bestTranscription.segments) {
            [out appendFormat:@"%@{\"w\":%@,\"t\":%.3f,\"d\":%.3f}", comma ? @"," : @"", quoted(s.substring), first + s.timestamp, s.duration];
            comma = YES;
        }
        [out appendString:@"]}"];
        return put(json, size, out);
    }
}
