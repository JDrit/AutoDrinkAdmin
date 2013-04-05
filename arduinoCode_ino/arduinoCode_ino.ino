#include <OneWire.h>
#define IBUTTON_ID_SIZE 8

OneWire ds(4); // One Wire for iButton on pin 4

unsigned long int time;             // the current time unit
unsigned long int billLastTime;     // last time the bill reader pulsed
unsigned long int serialLastTime;   // the timer for when the bills should be written to Serial
unsigned long timeOfLastPulseCoins; // the time of the last pulse from the coin reader
volatile int billsValue;             // counter for the bill reader
volatile int coinsValue;            // the value for the coin reader
int coinsChange;                    // 1 if the coin has had input, 0 otherwise
int billsChange;                    // 1 if the bill has had input, 0 otherwise
String result;                      // result from the iButton reader
byte ibutton_id[IBUTTON_ID_SIZE];   // data to hold the iButton ID

void setup()
{
  billLastTime = millis();
  serialLastTime = millis();
  timeOfLastPulseCoins = millis();
  billsValue = 0;
  coinsChange = 0;
  billsChange = 0;
  coinsValue = 0;
  Serial.begin(9600);
  pinMode(9,OUTPUT);
  //pinMode(10, INPUT);
  delay(500);
  digitalWrite(9, LOW);
  attachInterrupt(0, coinInserted, RISING);
  attachInterrupt(1, billInserted, RISING);
}

/*
 * interupt method for when the coin reader pulses
 */
void coinInserted() {
  coinsValue++;
  coinsChange = 1;
  timeOfLastPulseCoins = millis();
}

void billInserted() {
  time = millis();

  if(time - billLastTime > 50) {
    billsValue++;
    billsChange = 1;
    if(!digitalRead(9))
      digitalWrite(9, HIGH);
    serialLastTime = millis();
  }
  billLastTime = time;
}

void loop()
{
  
  if (Serial.available()) { // if the computer writes to the arduino
    Serial.println(Serial.read());
  }
  
  // clears & initialzes the iButton buffer
  for (int i = 0 ; i < IBUTTON_ID_SIZE ; i++) {
    ibutton_id[i] = 0;
  }
  
  // reads the iButton ID, if present
  if (ds.search(ibutton_id)) {
    for (int i = IBUTTON_ID_SIZE - 1 ; i >= 0 ; i--) {
      if (ibutton_id[i] < 0x10)
        result += '0';
      result += String(ibutton_id[i], HEX);
    }
    Serial.print("i:" + result);
    delay(1000);
  } else {
    ds.reset_search();
  }

  /*
  pulseIn(10, RISING);
  time = millis();

  if(time - billLastTime > 50)
  {
    billCounter++;
    if(!digitalRead(9))
      digitalWrite(9, HIGH);
    serialLastTime = millis();
  }
  else
  {
    if(billCounter != 0 && millis() - serialLastTime > 1000)
    {
      Serial.println("m:" + String(billCounter));
      billCounter = 0;
      digitalWrite(9,LOW);

    }
  }
  billLastTime = time;
  */ 
  if (billsChange == 1 && millis() - serialLastTime > 1000) {
    billsChange = 0;
    Serial.print("m:" + String(billsValue * 100));
    billsValue = 0;
  }
  
  if (coinsChange == 1 && millis() - timeOfLastPulseCoins > 1000) {
    coinsChange = 0;
    Serial.print("m:" + String(coinsValue));
    coinsValue = 0;
  }
  
}
