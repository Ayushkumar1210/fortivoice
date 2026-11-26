// Browser Web Speech API Service for Speech-to-Text and Text-to-Speech

class SpeechService {
  constructor() {
    this.recognition = null;
    this.synthesis = typeof window !== 'undefined' ? window.speechSynthesis : null;
    this.isListening = false;
    this.isSpeaking = false;
    this.voices = [];
    this.selectedVoice = null;
    this.language = 'en-US'; // default
    this.lastSpokeEndTime = 0;
    this.lastSpokenText = '';

    this._initSpeechRecognition();
    this._initVoices();
  }

  setLastSpokenText(text) {
    this.lastSpokenText = (text || '')
      .toLowerCase()
      .replace(/[^a-z0-9 ]/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  isSelfEcho(incomingText) {
    if (!this.lastSpokenText || !incomingText) return false;
    const incomingNorm = incomingText
      .toLowerCase()
      .replace(/[^a-z0-9 ]/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    if (!incomingNorm || incomingNorm.length < 3) return false;

    // Check if incoming text is contained inside recent AI speech
    if (this.lastSpokenText.includes(incomingNorm)) {
      return true;
    }

    // Check word overlap ratio
    const incomingWords = incomingNorm.split(' ').filter((w) => w.length > 2);
    if (incomingWords.length >= 2) {
      const matchCount = incomingWords.filter((w) => this.lastSpokenText.includes(w)).length;
      if (matchCount / incomingWords.length >= 0.65) {
        return true;
      }
    }
    return false;
  }

  _initSpeechRecognition() {
    if (typeof window === 'undefined') return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('Web Speech Recognition API is not supported in this browser.');
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = this.language;
    this.recognition.maxAlternatives = 1;
  }

  _initVoices() {
    if (!this.synthesis) return;

    const loadVoices = () => {
      this.voices = this.synthesis.getVoices();
    };

    loadVoices();
    if (this.synthesis.onvoiceschanged !== undefined) {
      this.synthesis.onvoiceschanged = loadVoices;
    }
  }

  setLanguage(langCode) {
    if (langCode === 'hi') {
      this.language = 'hi-IN';
    } else {
      this.language = 'en-US';
    }

    if (this.recognition) {
      this.recognition.lang = this.language;
    }
  }

  getVoicesForLang(langCode) {
    if (!this.voices || this.voices.length === 0) {
      this.voices = this.synthesis ? this.synthesis.getVoices() : [];
    }
    const prefix = langCode === 'hi' ? 'hi' : 'en';
    return this.voices.filter((v) => v.lang.startsWith(prefix));
  }

  // --- Speech to Text (Recognition) ---
  startListening({ onResult, onStart, onEnd, onError }) {
    if (!this.recognition) {
      this._initSpeechRecognition();
    }

    if (!this.recognition) {
      if (onError) onError('Speech Recognition not supported in this browser.');
      return false;
    }

    if (this.isSpeaking) {
      console.warn('SpeechService: Cannot start listening while speech synthesis is active');
      return false;
    }

    if (this.isListening) {
      this.stopListening();
    }

    this.recognition.lang = this.language;

    this.recognition.onstart = () => {
      this.isListening = true;
      if (onStart) onStart();
    };

    this.recognition.onresult = (event) => {
      // Acoustic Echo Guard: Discard input if agent is speaking or within 500ms cooldown
      if (this.isSpeaking || (Date.now() - this.lastSpokeEndTime < 500)) {
        return;
      }

      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      const cleanFinal = finalTranscript.trim();
      const cleanInterim = interimTranscript.trim();

      // Guard against self-voice echo loop
      if (cleanFinal && this.isSelfEcho(cleanFinal)) {
        console.warn('SpeechService: Blocked self-voice echo bleed-through:', cleanFinal);
        return;
      }

      if (onResult) {
        onResult({
          final: cleanFinal,
          interim: cleanInterim,
        });
      }
    };

    this.recognition.onerror = (event) => {
      console.warn('Speech recognition event error:', event.error);
      if (event.error !== 'no-speech') {
        if (onError) onError(event.error);
      }
    };

    this.recognition.onend = () => {
      this.isListening = false;
      if (onEnd) onEnd();
    };

    try {
      this.recognition.start();
      return true;
    } catch (err) {
      console.error('Failed to start recognition:', err);
      if (onError) onError(err.message);
      return false;
    }
  }

  stopListening() {
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch (e) {
        try {
          this.recognition.stop();
        } catch (err) {}
      }
    }
    this.isListening = false;
  }

  // --- Text to Speech (Synthesis) ---
  speak(text, { onStart, onEnd, onError, rate = 1.05, pitch = 1.0 } = {}) {
    if (!this.synthesis) {
      console.warn('Speech synthesis not supported');
      if (onError) onError('Speech synthesis not supported');
      return;
    }

    // Immediately stop microphone listening while agent speaks (prevents acoustic feedback)
    this.stopListening();
    this.cancelSpeech();

    // Clean text of markdown characters
    const cleanText = text
      .replace(/\*/g, '')
      .replace(/#/g, '')
      .replace(/`/g, '')
      .replace(/\[.*?\]\(.*?\)/g, '')
      .trim();

    if (!cleanText) return;

    this.setLastSpokenText(cleanText);

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = this.language;
    utterance.rate = rate;
    utterance.pitch = pitch;

    // Pick best voice for language
    const suitableVoices = this.getVoicesForLang(this.language === 'hi-IN' ? 'hi' : 'en');
    if (suitableVoices.length > 0) {
      // Prefer Google or Natural voices if present
      const preferred = suitableVoices.find(
        (v) => v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Premium')
      );
      utterance.voice = preferred || suitableVoices[0];
    }

    utterance.onstart = () => {
      this.isSpeaking = true;
      this.stopListening();
      if (onStart) onStart();
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      this.lastSpokeEndTime = Date.now();
      if (onEnd) onEnd();
    };

    utterance.onerror = (err) => {
      this.isSpeaking = false;
      this.lastSpokeEndTime = Date.now();
      console.error('Speech synthesis error:', err);
      if (onError) onError(err);
    };

    this.synthesis.speak(utterance);
  }

  cancelSpeech() {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {
        console.warn('Speech cancel error:', e);
      }
    }
    this.isSpeaking = false;
    this.lastSpokeEndTime = Date.now();
  }
}

export const speechService = new SpeechService();
