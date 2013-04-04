long int time;
long int lastTime;
int counter = 0;

void setup()
{
	Serial.begin(9600);
	pinMode(9,OUTPUT);
	pinMode(10, INPUT);
	delay(500);
	lastTime = millis();
        digitalWrite(9, LOW);
}

void loop()
{
	int num = pulseIn(10, RISING);
	//Serial.println(num);
	time = millis();
	if(time - lastTime > 1000)
	{
		//Serial.println(time - lastTime);
		counter++;
		if(!digitalRead(9))
			digitalWrite(9, HIGH);
	}
	else
	{
		if(counter != 0)
		{
			Serial.println(counter);
			counter = 0;
			digitalWrite(9,LOW);
		}
	}
	lastTime = time;
}
