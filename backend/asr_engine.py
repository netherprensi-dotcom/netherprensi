"""
ASR (Automatic Speech Recognition) Motoru
Ses tanıma ve komut algılama
"""

import pyaudio
from vosk import Model, KaldiRecognizer
import json
import threading
from queue import Queue

class ASREngine:
    def __init__(self, model_path="model"):
        """
        ASR motorunu başlat (Vosk kullanarak)
        """
        try:
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, 16000)
            self.recognizer.SetWords(self._get_keywords())
        except Exception as e:
            print(f"⚠️ Model yükleme hatası: {e}")
            self.model = None
        
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.listening = False
        self.recognition_queue = Queue()
        self.listener_thread = None
    
    def _get_keywords(self):
        """J.A.R.V.I.S komut anahtar kelimeleri"""
        keywords = [
            "uygulama aç",
            "oyun başlat",
            "ekranı kilitle",
            "bilgisayarı kapat",
            "selamlaşma",
            "dosya aç",
            "internet aç",
            "müzik çal",
            "ses artır",
            "ses azalt",
            "zamanı söyle",
            "hava durumu",
            "takvim",
            "ayarlar"
        ]
        return keywords
    
    def start_listening(self):
        """Arka planda dinlemeye başla"""
        if self.listening or not self.model:
            return
        
        self.listening = True
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4096
        )
        
        self.listener_thread = threading.Thread(
            target=self._listen_worker,
            daemon=True
        )
        self.listener_thread.start()
        print("🎤 Dinleme başladı...")
    
    def stop_listening(self):
        """Dinlemeyi durdur"""
        self.listening = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        print("🔇 Dinleme durduruldu")
    
    def _listen_worker(self):
        """Arka planda ses dinle ve tanı"""
        while self.listening:
            try:
                data = self.stream.read(4096, exception_on_overflow=False)
                
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    
                    if "result" in result and result["result"]:
                        text = " ".join([item["conf"] for item in result["result"]])
                        self.recognition_queue.put(text)
                    
                    if "text" in result:
                        command = result["text"].lower()
                        if command:
                            print(f"🎤 Algılanan: {command}")
                            self.recognition_queue.put(command)
            
            except Exception as e:
                print(f"Dinleme hatası: {e}")
    
    def get_command(self, timeout=None):
        """
        Sıradaki tanınan komutu al
        timeout: Bekleme süresi (saniye)
        """
        try:
            command = self.recognition_queue.get(timeout=timeout)
            return command
        except:
            return None
    
    def process_command(self, command):
        """
        Komutu işle ve kategori döndür
        """
        command = command.lower().strip()
        
        # Komut kategorileri
        if any(word in command for word in ["uygulama", "açı", "başlat", "oyun"]):
            return "launch_app", command
        
        elif any(word in command for word in ["kilitle", "kilit", "ekran"]):
            return "lock_screen", command
        
        elif any(word in command for word in ["kapat", "kapatı"]):
            return "shutdown", command
        
        elif any(word in command for word in ["zamanı", "saat", "ne vakit"]):
            return "time", command
        
        elif any(word in command for word in ["hava", "durumu", "hava durumu"]):
            return "weather", command
        
        elif any(word in command for word in ["müzik", "çal", "şarkı"]):
            return "music", command
        
        elif any(word in command for word in ["ses", "artır", "azalt", "kıs"]):
            return "volume", command
        
        else:
            return "unknown", command
    
    def close(self):
        """Kaynakları kapat"""
        self.stop_listening()
        if self.stream:
            self.stream.close()
        self.p.terminate()

# Test
if __name__ == "__main__":
    asr = ASREngine()
    asr.start_listening()
    
    try:
        while True:
            cmd = asr.get_command(timeout=1)
            if cmd:
                category, text = asr.process_command(cmd)
                print(f"Kategori: {category}, Metin: {text}")
    except KeyboardInterrupt:
        asr.close()
