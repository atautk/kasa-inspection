#include <LiquidCrystal.h>

// ===================================================
// PIN TANIMLARI (kendi bağlantına göre değiştir)
// ===================================================

const int BUZZER_PIN = 8;
const int ALARM_LED_PIN = 7;
const int BUTTON_PIN = 2;

const int ALARM_FREQUENCY = 2000; // Hz (piezo alarm tonu)

// LCD pinleri (4-bit mod)
const int LCD_RS = 12;
const int LCD_EN = 11;
const int LCD_D4 = 6;
const int LCD_D5 = 5;
const int LCD_D6 = 4;
const int LCD_D7 = 3;

// ===================================================
// LCD (Direkt Paralel 16x2, HD44780 uyumlu)
// ===================================================

LiquidCrystal lcd(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7);

// ===================================================
// Seri Okuma Buffer
// ===================================================

String inputLine = "";

// ===================================================
// Kayan Yazı (Scroll) Durumu
// ===================================================

String ngText = "";
int scrollIndex = 0;
unsigned long lastScrollTime = 0;
const unsigned long SCROLL_INTERVAL = 400; // ms

// ===================================================
// Alarm / Susturma Durumu
// ===================================================

bool alarmActive = false;
bool muted = false;
String lastNgNames = "";

// ===================================================
// Buton (Onayla / Sustur) - Debounce
// ===================================================

int lastRawButtonState = HIGH;   // INPUT_PULLUP -> boşta HIGH
unsigned long lastDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY = 50; // ms

// ===================================================
// Buzzer - Kesikli Çalma (Bip - Sessizlik - Bip...)
// ===================================================

const unsigned long BUZZER_ON_MS = 200;
const unsigned long BUZZER_OFF_MS = 200;

bool buzzerToneOn = false;
unsigned long lastBuzzerToggleTime = 0;

// ===================================================
// SETUP
// ===================================================

void setup() {

  Serial.begin(9600);

  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(ALARM_LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  digitalWrite(ALARM_LED_PIN, LOW);
  noTone(BUZZER_PIN);

  lcd.begin(16, 2);

  lcd.setCursor(0, 0);
  lcd.print("Kasa Inspection");
  lcd.setCursor(0, 1);
  lcd.print("Baslatiliyor...");
}

// ===================================================
// LOOP
// ===================================================

void loop() {

  readSerial();
  checkButton();
  updateScroll();
  updateBuzzer();
}

// -------------------------------------------------
// Seri Porttan Satır Oku
// -------------------------------------------------

void readSerial() {

  while (Serial.available() > 0) {

    char c = Serial.read();

    if (c == '\n') {

      handleLine(inputLine);
      inputLine = "";

    } else if (c != '\r') {

      inputLine += c;
    }
  }
}

// -------------------------------------------------
// Gelen Satırı İşle
//
// Protokol:
//   "OK"          -> tüm gözler dolu/boş beklenen gibi (alarm yok)
//   "NG:G02,G04"  -> belirtilen gözler beklenmeyen durumda
//   "WAIT"        -> kamera hizalanmadı / kasa görünmüyor (alarm yok)
// -------------------------------------------------

void handleLine(String line) {

  line.trim();

  if (line == "OK") {

    setOk();

  } else if (line == "WAIT") {

    setWaiting();

  } else if (line.startsWith("NG:")) {

    String names = line.substring(3);
    setNg(names);
  }
}

// -------------------------------------------------
// OK Durumu
// -------------------------------------------------

void setOk() {

  alarmActive = false;
  muted = false;
  lastNgNames = "";

  digitalWrite(ALARM_LED_PIN, LOW);
  updateBuzzer();

  ngText = "";
  scrollIndex = 0;

  lcd.setCursor(0, 0);
  lcd.print("Tum Gozler OK   ");
  lcd.setCursor(0, 1);
  lcd.print("                ");
}

// -------------------------------------------------
// Bekleme Durumu (Kamera Hizalanmadı / Kasa Yok)
// -------------------------------------------------

void setWaiting() {

  alarmActive = false;
  muted = false;
  lastNgNames = "";

  digitalWrite(ALARM_LED_PIN, LOW);
  updateBuzzer();

  ngText = "";
  scrollIndex = 0;

  lcd.setCursor(0, 0);
  lcd.print("Kamera Bekliyor ");
  lcd.setCursor(0, 1);
  lcd.print("                ");
}

// -------------------------------------------------
// NG Durumu
// -------------------------------------------------

void setNg(String names) {

  // Aynı sorun devam ediyorsa (isim listesi değişmediyse)
  // ve operatör zaten susturduysa, tekrar sesli alarma geçme.
  // Yeni/farklı bir NG geldiğinde ise susturma sıfırlanır.

  if (names != lastNgNames) {

    muted = false;
  }

  lastNgNames = names;
  alarmActive = true;

  digitalWrite(ALARM_LED_PIN, HIGH);
  updateBuzzer();

  lcd.setCursor(0, 0);

  if (muted) {
    lcd.print("NG (Susturuldu) ");
  } else {
    lcd.print("HATA! NG Goz:   ");
  }

  ngText = names + "   ";  // sona boşluk, scroll geçişi için
  scrollIndex = 0;

  showScrollLine();
}

// -------------------------------------------------
// Buzzer'ı Güncel Duruma Göre Ayarla (Kesikli)
// -------------------------------------------------

void updateBuzzer() {

  bool shouldSound = alarmActive && !muted;

  if (!shouldSound) {

    noTone(BUZZER_PIN);
    buzzerToneOn = false;

    return;
  }

  unsigned long now = millis();
  unsigned long elapsed = now - lastBuzzerToggleTime;

  if (buzzerToneOn) {

    if (elapsed >= BUZZER_ON_MS) {

      noTone(BUZZER_PIN);
      buzzerToneOn = false;
      lastBuzzerToggleTime = now;
    }

  } else {

    if (elapsed >= BUZZER_OFF_MS) {

      tone(BUZZER_PIN, ALARM_FREQUENCY);
      buzzerToneOn = true;
      lastBuzzerToggleTime = now;
    }
  }
}

// -------------------------------------------------
// Buton (Onayla / Sustur) - Debounce + Kenar Algılama
// -------------------------------------------------

void checkButton() {

  int reading = digitalRead(BUTTON_PIN);

  if (reading != lastRawButtonState) {

    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY) {

    // INPUT_PULLUP: butona basılınca LOW olur.
    // Sadece HIGH -> LOW geçişinde (basma anında) tetikle.

    static int stableState = HIGH;

    if (reading != stableState) {

      stableState = reading;

      if (stableState == LOW && alarmActive) {

        muted = true;

        updateBuzzer();

        lcd.setCursor(0, 0);
        lcd.print("NG (Susturuldu) ");
      }
    }
  }

  lastRawButtonState = reading;
}

// -------------------------------------------------
// LCD İkinci Satırı Kaydır (uzun NG listeleri için)
// -------------------------------------------------

void updateScroll() {

  if (ngText == "") return;

  if (millis() - lastScrollTime < SCROLL_INTERVAL) return;

  lastScrollTime = millis();

  scrollIndex++;

  if (scrollIndex >= (int)ngText.length()) {
    scrollIndex = 0;
  }

  showScrollLine();
}

void showScrollLine() {

  String doubled = ngText + ngText;
  String visible = doubled.substring(scrollIndex, scrollIndex + 16);

  lcd.setCursor(0, 1);
  lcd.print(visible);
}
