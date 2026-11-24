# Dizzy voice delay diagnosis

Verified18 November2026. The latest live run passed identity, head movement and general conversation with spoken output.

## Findings

- The original model intermittently returned actual503 high-demand errors. A same-configuration benchmark also succeeded in1.29s; this was not a consistent microphone or credential failure.
- The previous20s request limit with two attempts could wait about40s for one model operation.
- Fresh Piper processes reloaded the speech engine/model for each reply. Text results also waited for playback completion.

## Changes

- Identity and system instruction: “Dizzy, a pet buddy created and developed by Heshwa for Yoga.” Both local identity replies and the Gemini/Ollama system message use this identity. Google is identified as the language-model supplier, not the pet creator.
- Explicit, single head/hand/music commands use the shared local action interface. Negated, conditional, compound, scheduled and unknown requests stay with the model. Failures are never confirmed as successes.
- Primary remains gemini-3.1-flash-lite. A transient error before any tools execute can switch once to gemini-3.5-flash-lite. After a primary failure, a60s cooldown avoids hammering that model. No provider switch or turn replay occurs after tools execute.
- Requests have a10s SDK deadline, one SDK attempt and an11s outer call limit. Total model/tool processing is bounded at25s. API quota, authentication, request-configuration, overload and timeout failures have distinct feedback.
- The client connection and Piper voice model are reused. Completed conversation history retains user/final-answer text rather than all prior tool/thinking payloads.
- The recognized transcript and model reply become visible before playback finishes; the recording button shows Speaking during playback. Stage timings and sanitized model-call diagnostics are included in results.

## Live measurements

| Scenario | Reply preparation | Speech generation | Approx. synthesis-ready time |
|---|---:|---:|---:|
|Who developed you?|308ms|523ms|831ms|
|Can you rotate your head to the right?|194ms|80ms|274ms|
|Tell Yoga one cheerful thought for the day.|9197ms|245ms|9442ms|

Re-transcribing an existing real microphone recording took725ms. The table starts after text is available. Synthesis-ready time is reply+speech-queue+synthesis time; it excludes microphone recognition and small output-device startup overhead. Whole-request time also includes actually speaking the words, and should not be confused with delay before speech.

The general-conversation run deliberately captured the real outage:3.1 returned503 after1333ms, fallback3.5 answered in7682ms, and spoken output completed successfully. General cloud conversation is therefore still slower when Google is overloaded; these changes do not claim to repair Google’s capacity. Local commands and creator identity do not require Google.

## Validation

-130 automated tests pass, including safe local routing, false-confirmation prevention, fallback/cooldown, quota classification, and no repeated actions after tool execution.
- Live head command reached35° and played its confirmation. Creator reply named Heshwa and Yoga. General conversation succeeded using fallback.
- The first low-deadline test failed with Google400 because the SDK deadline was below Google’s10s minimum. It was corrected and the successful live run repeated; voice-speed-first-run.json retains the failure.
- No billing tier, API key or hardware changed. Both configured models have a documented free tier; availability and quota remain account-dependent.

Evidence: voice-latency-model-benchmark.json, voice-speed-first-run.json, voice-speed-live-checks.json. Repeat with the project environment: `python scripts/check_voice_speed.py` (speaks sample replies and turns the head).

Primary sources: [thinking configuration](https://aistudio.google.com/docs/thinking#thinking-levels), [model catalogue](https://aistudio.google.com/docs/models), [3.5 Flash-Lite pricing/free tier](https://aistudio.google.com/docs/pricing#gemini-3.5-flash-lite), [Google troubleshooting](https://aistudio.google.com/docs/troubleshooting).
