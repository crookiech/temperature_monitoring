#include "main.h"

Sensor sensors[MAX_SENSORS];
Sensor previousSensors[MAX_SENSORS];
uint8_t actualSensorCount = 0;
uint8_t previousSensorCount = 0;

volatile uint32_t msTicks = 0;
volatile uint32_t error_counter = 0;

static unsigned char received_string[100];
static int char_index = 0;
static int string_received = 0;
static uint32_t lastDataSend = 0;
static uint32_t last_blink_time = 0;
static uint8_t blinking_active = 0;

LM75A_Sensor lm75a_sensor = {0, 0.0f, 0, 0};

void SysTick_Handler(void) {
    msTicks++;
}

void Delay(uint32_t dlyTicks) {
    uint32_t curTicks;
    curTicks = msTicks;
    while ((msTicks - curTicks) < dlyTicks) { __NOP(); }
}

void SystemCoreClockConfigure(void) {
    RCC->CR |= ((uint32_t)RCC_CR_HSEON);                    
    while ((RCC->CR & RCC_CR_HSERDY) == 0);
    RCC->CFGR = RCC_CFGR_SW_HSE;                             
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_HSE);
    RCC->CFGR = RCC_CFGR_HPRE_DIV1;
    RCC->CFGR |= RCC_CFGR_PPRE1_DIV1;
    RCC->CFGR |= RCC_CFGR_PPRE2_DIV1;
    RCC->CR &= ~RCC_CR_PLLON;
    RCC->CFGR &= ~(RCC_CFGR_PLLSRC | RCC_CFGR_PLLMULL);
    RCC->CFGR |= (RCC_CFGR_PLLSRC_HSE | RCC_CFGR_PLLMULL9);
    RCC->CR |= RCC_CR_PLLON;                                
    while((RCC->CR & RCC_CR_PLLRDY) == 0) __NOP();
    RCC->CFGR &= ~RCC_CFGR_SW;                               
    RCC->CFGR |= RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL);  
}

void LED_Init(void) {
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;
    GPIOA->CRL &= ~GPIO_CRL_CNF5;
    GPIOA->CRL &= ~GPIO_CRL_MODE5;
    GPIOA->CRL |= GPIO_CRL_MODE5_1;
    GPIOA->CRL &= ~GPIO_CRL_CNF5;
    GPIOA->BSRR = GPIO_BSRR_BR5;
}

void LED_ON(void) {
    GPIOA->BSRR = GPIO_BSRR_BS5;
}

void LED_OFF(void) {
    GPIOA->BSRR = GPIO_BSRR_BR5;
}

void LED_BLINKING(void) {
    if (GPIOA->ODR & GPIO_ODR_ODR5) {
        GPIOA->BSRR = GPIO_BSRR_BR5;
    } else {
        GPIOA->BSRR = GPIO_BSRR_BS5;
    }
}

void UpdateLEDByTemperature(float max_temp) {
    if(max_temp > TEMP_THRESHOLD) {
        if(!blinking_active) {
            blinking_active = 1;
            last_blink_time = msTicks;
            LED_ON();
        } else {
            if((msTicks - last_blink_time) >= BLINK_INTERVAL_MS) {
                LED_BLINKING();
                last_blink_time = msTicks;
            }
        }
    } else {
        if(blinking_active) {
            blinking_active = 0;
            LED_OFF();
        }
    }
}

void Init_Sensors(void) {
    for (uint8_t i = 0; i < MAX_SENSORS; i++) {
        sensors[i].raw_temp = 0x0;
        sensors[i].temp = 0.0;
        sensors[i].crc8_rom = 0x0;
        sensors[i].crc8_data = 0x0;
        sensors[i].crc8_rom_error = 0x0;
        sensors[i].crc8_data_error = 0x0;
        for (uint8_t j = 0; j < 8; j++) {
            sensors[i].ROM_code[j] = 0x00;
            previousSensors[i].ROM_code[j] = 0x00;
        }
        for (uint8_t j = 0; j < 9; j++) {
            sensors[i].scratchpad_data[j] = 0x00;
        }
    }
}

void SaveCurrentSensorState(void) {
    previousSensorCount = actualSensorCount;
    for (uint8_t i = 0; i < actualSensorCount; i++) {
        for (uint8_t j = 0; j < 8; j++) {
            previousSensors[i].ROM_code[j] = sensors[i].ROM_code[j];
        }
    }
}

int CompareROMCodes(const uint8_t* rom1, const uint8_t* rom2) {
    for (uint8_t i = 0; i < 8; i++) {
        if (rom1[i] != rom2[i]) {
            return 0;
        }
    }
    return 1;
}

void SendROMCode(const uint8_t* rom_code) {
    char rom_byte[4];
    for (uint8_t j = 0; j < 8; j++) {
        sprintf(rom_byte, "%02X", rom_code[j]);
        USART_SendString(rom_byte);
    }
}

void CompareAndReportSensorChanges(void) {
    uint8_t found;
    for (uint8_t i = 0; i < previousSensorCount; i++) {
        found = 0;
        for (uint8_t j = 0; j < actualSensorCount; j++) {
            if (CompareROMCodes(previousSensors[i].ROM_code, sensors[j].ROM_code)) {
                found = 1;
                break;
            }
        }
        if (!found) {
            USART_SendString("\r\nSensor disconnected: ");
            SendROMCode(previousSensors[i].ROM_code);
            USART_SendString("\r\n");
        }
    }
    for (uint8_t i = 0; i < actualSensorCount; i++) {
        found = 0;
        for (uint8_t j = 0; j < previousSensorCount; j++) {
            if (CompareROMCodes(sensors[i].ROM_code, previousSensors[j].ROM_code)) {
                found = 1;
                break;
            }
        }
        if (!found) {
            USART_SendString("\r\nSensor connected: ");
            SendROMCode(sensors[i].ROM_code);
            USART_SendString("\r\n");
        }
    }
}

uint8_t CheckAndUpdateSensors(void) {
    uint8_t newCount = 0;
    Sensor tempSensors[MAX_SENSORS];
    for (uint8_t i = 0; i < MAX_SENSORS; i++) {
        for (uint8_t j = 0; j < 8; j++) {
            tempSensors[i].ROM_code[j] = 0x00;
        }
    }
    newCount = Search_ROM(SEARCH_ROM, tempSensors);
    if (newCount != actualSensorCount) {
        SaveCurrentSensorState();
        actualSensorCount = newCount;
        for (uint8_t i = 0; i < actualSensorCount; i++) {
            for (uint8_t j = 0; j < 8; j++) {
                sensors[i].ROM_code[j] = tempSensors[i].ROM_code[j];
            }
        }
        for (uint8_t i = 0; i < actualSensorCount; i++) {
            ds18b20_Init(1, sensors[i].ROM_code, 0x1E, 0xE2, RESOLUTION_12BIT);
        }
        CompareAndReportSensorChanges();
        return 1;
    }
    return 0;
}

uint8_t ReadTemperatureFromSensor(uint8_t index) {
    uint8_t data[9];
    if (index >= actualSensorCount) return 0;
    if (ds18b20_Reset() != 0) return 0;
    ds18b20_WriteByte(MATCH_ROM);
    for (uint8_t i = 0; i < 8; i++) {
        ds18b20_WriteByte(sensors[index].ROM_code[i]);
    }
    ds18b20_WriteByte(0xBE);
    for (uint8_t i = 0; i < 9; i++) {
        data[i] = ds18b20_ReadByte();
        sensors[index].scratchpad_data[i] = data[i];
    }
    sensors[index].crc8_data_error = Compute_CRC8(data, 9) != 0;
    if (!sensors[index].crc8_data_error) {
        switch(data[4]) {
            case 0x1F:  
                sensors[index].raw_temp = ((uint16_t)data[1] << 8) | data[0];
                sensors[index].temp = sensors[index].raw_temp * 0.5;
                break;
            case 0x3F:
                sensors[index].raw_temp = ((uint16_t)data[1] << 8) | data[0];
                sensors[index].temp = sensors[index].raw_temp * 0.25;
                break;
            case 0x5F:
                sensors[index].raw_temp = ((uint16_t)data[1] << 8) | data[0];
                sensors[index].temp = sensors[index].raw_temp * 0.125;
                break;
            case 0x7F:
                sensors[index].raw_temp = ((uint16_t)data[1] << 8) | data[0];
                sensors[index].temp = sensors[index].raw_temp * 0.0625;
                break;
            default:
                sensors[index].raw_temp = ((uint16_t)data[1] << 8) | data[0];
                sensors[index].temp = sensors[index].raw_temp * 0.0625;
                break;
        }
        return 1;
    }
    return 0;
}

void StartTemperatureConversion(uint8_t index) {
    if (index >= actualSensorCount) return;
    if (ds18b20_Reset() == 0) {
        ds18b20_WriteByte(MATCH_ROM);
        for (uint8_t i = 0; i < 8; i++) {
            ds18b20_WriteByte(sensors[index].ROM_code[i]);
        }
        ds18b20_WriteByte(0x44);
    }
}

void USART_Init(void) {
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN; 
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;
    GPIOA->CRL &= (~GPIO_CRL_CNF2_0); 
    GPIOA->CRL |= (GPIO_CRL_CNF2_1 | GPIO_CRL_MODE2);
    GPIOA->CRL &= (~GPIO_CRL_CNF3_0);
    GPIOA->CRL |= GPIO_CRL_CNF3_1;
    GPIOA->CRL &= (~(GPIO_CRL_MODE3));
    GPIOA->BSRR |= GPIO_ODR_ODR3;
    USART2->BRR = 7500;
    USART2->CR1 |= USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
    USART2->CR2 = 0;
    USART2->CR3 = 0;
}

void USART_SendByte(unsigned char data) {
    while ((USART2->SR & USART_SR_TXE) == 0) {}
    USART2->DR = data;
}

void USART_SendString(const char* str) {
    while (*str) {
        USART_SendByte(*str++);
    }
}

static void USART_SendChar(char c) {
    while ((USART2->SR & USART_SR_TXE) == 0) {}
    USART2->DR = c;
}

unsigned char USART_ReceiveByte(void) {
    while ((USART2->SR & USART_SR_RXNE) == 0) {}
    return (unsigned char)USART2->DR;
}

void SendTemperatureData(void) {
    USART_SendString("\r\n=== TEMPERATURE REPORT ===\r\n");
    
    USART_SendString("DS18B20 Sensors count: ");
    char count_str[4];
    sprintf(count_str, "%d", actualSensorCount);
    USART_SendString(count_str);
    USART_SendString("\r\n");
    
    for (uint8_t i = 0; i < actualSensorCount; i++) {
        USART_SendString("DS18B20 Sensor ");
        char sensor_num[4];
        sprintf(sensor_num, "%d", i);
        USART_SendString(sensor_num);
        USART_SendString(" (");
        for (uint8_t j = 0; j < 8; j++) {
            char rom_byte[4];
            sprintf(rom_byte, "%02X", sensors[i].ROM_code[j]);
            USART_SendString(rom_byte);
        }
        USART_SendString("): ");
        char temp_str[20];
        sprintf(temp_str, "%.2f C\r\n", sensors[i].temp);
        USART_SendString(temp_str);
    }
    
    USART_SendString("LM75A Sensor: ");
    if(lm75a_sensor.present) {
        char lm75a_str[30];
        sprintf(lm75a_str, "Address 0x%02X: %.2f C\r\n", lm75a_sensor.address, lm75a_sensor.temp);
        USART_SendString(lm75a_str);
    } else {
        USART_SendString("Not found\r\n");
    }
    
    USART_SendString("===========================\r\n");
}

void ProcessReceivedString(void) {
    if (strcmp((char*)received_string, "status") == 0) {
        SendTemperatureData();
    } else if (strcmp((char*)received_string, "help") == 0) {
        USART_SendString("\r\nCommands:\r\n");
        USART_SendString("  status - Show all temperatures\r\n");
        USART_SendString("  help   - Show this help\r\n");
    }
}

int main(void) {
    uint8_t i = 0;
    uint32_t lastSensorRead = 0;
    uint32_t lastSensorCheck = 0;
    uint32_t lastLM75ARead = 0;
    float max_temperature = 0.0f;
    unsigned char received_byte;
    
    SystemCoreClockConfigure();
    SystemCoreClockUpdate();
    SysTick_Config(SystemCoreClock / 1000000);
    
    ds18b20_PortInit();
    I2C_Init();
    LED_Init();
    USART_Init();
    
    while (ds18b20_Reset());
    Init_Sensors();
    
    actualSensorCount = Search_ROM(SEARCH_ROM, sensors);
    SaveCurrentSensorState();
    
    USART_SendString("\r\n=== SYSTEM START ===\r\n");
    USART_SendString("Found ");
    char count_str[4];
    sprintf(count_str, "%d", actualSensorCount);
    USART_SendString(count_str);
    USART_SendString(" DS18B20 sensors\r\n");
    
    for (i = 0; i < actualSensorCount; i++) {
        ds18b20_Init(1, sensors[i].ROM_code, 0x1E, 0xE2, RESOLUTION_12BIT);
    }
    
    lm75a_sensor.address = LM75A_CheckAnyDevice();
    if(lm75a_sensor.address != 0) {
        lm75a_sensor.present = 1;
        USART_SendString("LM75A sensor found at address 0x");
        char addr_str[4];
        sprintf(addr_str, "%02X\r\n", lm75a_sensor.address);
        USART_SendString(addr_str);
    } else {
        lm75a_sensor.present = 0;
        USART_SendString("LM75A sensor not found\r\n");
    }
    
    for (i = 0; i < actualSensorCount; i++) {
        StartTemperatureConversion(i);
    }
    
    lastSensorRead = msTicks;
    lastSensorCheck = msTicks;
    lastDataSend = msTicks;
    lastLM75ARead = msTicks;
    
    while (1) {
        if (USART2->SR & USART_SR_RXNE) {
            received_byte = USART_ReceiveByte();
            USART_SendChar(received_byte);
            if ((received_byte == '\r') || (received_byte == '\n')) {
                if (char_index > 0) {
                    USART_SendString("\r\n");
                    received_string[char_index] = '\0';
                    ProcessReceivedString();
                    char_index = 0;
                    string_received = 1;
                }
            }
            else if (received_byte == '\b' || received_byte == 0x7F) {
                if (char_index > 0) {
                    char_index--;
                    USART_SendString("\b \b");
                }
            }
            else {
                if (char_index < 99) {
                    received_string[char_index] = received_byte;
                    char_index++;
                }
            }
        }
        
        if (msTicks - lastSensorCheck > SENSOR_CHECK_INTERVAL) {
            lastSensorCheck = msTicks;
            
            if (CheckAndUpdateSensors()) {
                for (i = 0; i < actualSensorCount; i++) {
                    StartTemperatureConversion(i);
                }
                lastSensorRead = msTicks;
            }
        }
        
        if (msTicks - lastSensorRead > TEMP_READ_INTERVAL) {
            lastSensorRead = msTicks;
            max_temperature = 0.0f;
            
            for (i = 0; i < actualSensorCount; i++) {
                if (ReadTemperatureFromSensor(i)) {
                    if (sensors[i].temp > max_temperature) {
                        max_temperature = sensors[i].temp;
                    }
                } else {
                    sensors[i].temp = 0.0;
                    sensors[i].raw_temp = 0;
                    sensors[i].crc8_data_error = 1;
                }
            }
            
            for (i = 0; i < actualSensorCount; i++) {
                StartTemperatureConversion(i);
            }
        }
        
        if (msTicks - lastLM75ARead > 500000) {
            lastLM75ARead = msTicks;
            if(lm75a_sensor.present) {
                if(LM75A_ReadTemperature(lm75a_sensor.address, &lm75a_sensor.temp)) {
                    if(lm75a_sensor.temp > max_temperature) {
                        max_temperature = lm75a_sensor.temp;
                    }
                }
            } else {
                lm75a_sensor.address = LM75A_CheckAnyDevice();
                lm75a_sensor.present = (lm75a_sensor.address != 0);
                if(lm75a_sensor.present) {
                    USART_SendString("\r\nLM75A sensor connected!\r\n");
                }
            }
        }
        
        UpdateLEDByTemperature(max_temperature);
        
        if (msTicks - lastDataSend > 5000000) {
            lastDataSend = msTicks;
            SendTemperatureData();
        }
        
        Delay(10);
    }
}