#include "lm75a.h"

extern volatile uint32_t msTicks;
extern volatile uint32_t error_counter;

#define _RCC_I2C1_CLK_ENABLE()   do { \
    __IO uint32_t tmpreg; \
    SET_BIT(RCC->APB1ENR, RCC_APB1ENR_I2C1EN);\
    tmpreg = READ_BIT(RCC->APB1ENR, RCC_APB1ENR_I2C1EN);\
    (void)tmpreg; \
} while(0U)

#define _RCC_AFIO_CLK_ENABLE()   do { \
    __IO uint32_t tmpreg; \
    SET_BIT(RCC->APB2ENR, RCC_APB2ENR_AFIOEN);\
    tmpreg = READ_BIT(RCC->APB2ENR, RCC_APB2ENR_AFIOEN);\
    (void)tmpreg; \
} while(0U)
  
#define _RCC_GPIOB_CLK_ENABLE()   do { \
    __IO uint32_t tmpreg; \
    SET_BIT(RCC->APB2ENR, RCC_APB2ENR_IOPBEN);\
    tmpreg = READ_BIT(RCC->APB2ENR, RCC_APB2ENR_IOPBEN);\
    (void)tmpreg; \
} while(0U)

void Delay_US(uint32_t us) {
    uint32_t start = msTicks;
    while ((msTicks - start) < us) { __NOP(); }
}

void I2C_Init(void) {
    _RCC_AFIO_CLK_ENABLE();
    _RCC_GPIOB_CLK_ENABLE();
    
    SET_BIT(GPIOB->CRL, GPIO_CRL_CNF7_1 | GPIO_CRL_CNF6_1 | GPIO_CRL_CNF7_0 | GPIO_CRL_CNF6_0 |\
            GPIO_CRL_MODE7_1 | GPIO_CRL_MODE6_1 | GPIO_CRL_MODE7_0 | GPIO_CRL_MODE6_0);
    
    MODIFY_REG(I2C1->CR1, I2C_CR1_SMBUS | I2C_CR1_SMBTYPE | I2C_CR1_ENARP, I2C_MODE_I2C);
    
    _RCC_I2C1_CLK_ENABLE();
    
    CLEAR_BIT(I2C1->CR1, I2C_CR1_PE);
    SET_BIT(I2C1->CR1, I2C_CR1_SWRST);
    CLEAR_BIT(I2C1->CR1, I2C_CR1_SWRST);
    
    MODIFY_REG(I2C1->CR2, I2C_CR2_FREQ, 36);
    MODIFY_REG(I2C1->TRISE, I2C_TRISE_TRISE, 36 + 1);
    MODIFY_REG(I2C1->CCR, (I2C_CCR_FS | I2C_CCR_DUTY | I2C_CCR_CCR), 600);
    
    SET_BIT(I2C1->CR1, I2C_CR1_ACK);
    MODIFY_REG(I2C1->OAR1, 0xFFFF, I2C_OWNADDRESS1_7BIT);
    MODIFY_REG(I2C1->OAR2, I2C_OAR2_ADD2, 0);
    
    SET_BIT(I2C1->CR1, I2C_CR1_PE);
}

void I2C_Reset(void) {
    CLEAR_BIT(I2C1->CR1, I2C_CR1_PE);
    SET_BIT(I2C1->CR1, I2C_CR1_SWRST);
    CLEAR_BIT(I2C1->CR1, I2C_CR1_SWRST);
    MODIFY_REG(I2C1->CR2, I2C_CR2_FREQ, 36);
    MODIFY_REG(I2C1->TRISE, I2C_TRISE_TRISE, 36 + 1);
    MODIFY_REG(I2C1->CCR, (I2C_CCR_FS | I2C_CCR_DUTY | I2C_CCR_CCR), 120);
    
    SET_BIT(I2C1->CR1, I2C_CR1_ACK);
    MODIFY_REG(I2C1->OAR1, 0xFFFF, I2C_OWNADDRESS1_7BIT);
    
    SET_BIT(I2C1->CR1, I2C_CR1_PE);
}

void I2C_WriteData(uint8_t addr, uint8_t *buf, uint16_t bytes_count) {
    uint16_t i;
    CLEAR_BIT(I2C1->CR1, I2C_CR1_POS);
    SET_BIT(I2C1->CR1, I2C_CR1_ACK);
    SET_BIT(I2C1->CR1, I2C_CR1_START);
    
    while(!READ_BIT(I2C1->SR1, I2C_SR1_SB));
    (void) I2C1->SR1;
    
    I2C1->DR = SLAVE_OWN_ADDRESS | I2C_REQUEST_WRITE;
    
    while(!READ_BIT(I2C1->SR1, I2C_SR1_ADDR));
    (void) I2C1->SR1;
    (void) I2C1->SR2;
    
    I2C1->DR = addr;
    while(!READ_BIT(I2C1->SR1, I2C_SR1_TXE)){}
    
    for(i = 0; i < bytes_count; i++) {
        I2C1->DR = buf[i];
        while(!READ_BIT(I2C1->SR1, I2C_SR1_TXE)){}
    }
    SET_BIT(I2C1->CR1, I2C_CR1_STOP);
}

void I2C_ReadData(uint8_t addr, uint8_t *buf, uint16_t bytes_count) {
    uint16_t i;
    CLEAR_BIT(I2C1->CR1, I2C_CR1_POS);
    SET_BIT(I2C1->CR1, I2C_CR1_ACK);
    SET_BIT(I2C1->CR1, I2C_CR1_START);
    
    while(!READ_BIT(I2C1->SR1, I2C_SR1_SB));
    (void) I2C1->SR1;
    
    I2C1->DR = SLAVE_OWN_ADDRESS | I2C_REQUEST_WRITE;
    while(!READ_BIT(I2C1->SR1, I2C_SR1_ADDR));
    (void) I2C1->SR1;
    (void) I2C1->SR2;
    
    I2C1->DR = LM75B_Temp;
    while(!READ_BIT(I2C1->SR1, I2C_SR1_TXE)){}
    
    SET_BIT(I2C1->CR1, I2C_CR1_START);
    while(!READ_BIT(I2C1->SR1, I2C_SR1_SB));
    (void) I2C1->SR1;
    
    I2C1->DR = SLAVE_OWN_ADDRESS | I2C_REQUEST_READ;
    while(!READ_BIT(I2C1->SR1, I2C_SR1_ADDR));
    (void) I2C1->SR1;
    (void) I2C1->SR2;
    
    for(i = 0; i < bytes_count; i++) {
        if(i < (bytes_count-1)) {
            while(!READ_BIT(I2C1->SR1, I2C_SR1_RXNE)){}
            buf[i] = READ_BIT(I2C1->DR, I2C_DR_DR);
        } else {
            CLEAR_BIT(I2C1->CR1, I2C_CR1_ACK);
            SET_BIT(I2C1->CR1, I2C_CR1_STOP);
            while(!READ_BIT(I2C1->SR1, I2C_SR1_RXNE)){}
            buf[i] = READ_BIT(I2C1->DR, I2C_DR_DR);
        }
    }
}

uint8_t I2C_IsDeviceReady(uint8_t devAddr) {
    uint32_t timeout = 10000;
    uint8_t ready = 0;
    
    I2C1->SR1 &= ~(I2C_SR1_AF | I2C_SR1_BERR | I2C_SR1_ARLO | I2C_SR1_OVR);
    
    SET_BIT(I2C1->CR1, I2C_CR1_START);
    
    while(!READ_BIT(I2C1->SR1, I2C_SR1_SB) && timeout--);
    if(timeout == 0) {
        SET_BIT(I2C1->CR1, I2C_CR1_STOP);
        return 0;
    }
    
    I2C1->DR = (devAddr << 1) | I2C_REQUEST_WRITE;
    
    timeout = 5000;
    while(!READ_BIT(I2C1->SR1, I2C_SR1_ADDR) && !READ_BIT(I2C1->SR1, I2C_SR1_AF) && timeout--);
    
    if(READ_BIT(I2C1->SR1, I2C_SR1_ADDR)) {
        ready = 1;
        (void)I2C1->SR2;
    }
    
    SET_BIT(I2C1->CR1, I2C_CR1_STOP);
    
    I2C1->SR1 &= ~(I2C_SR1_AF | I2C_SR1_BERR | I2C_SR1_ARLO);
    
    return ready;
}

uint8_t LM75A_CheckAnyDevice(void) {
    uint8_t addr;
    
    for(addr = LM75A_ADDR_START; addr <= LM75A_ADDR_END; addr++) {
        if(I2C_IsDeviceReady(addr)) {
            return addr;
        }
    }
    return 0;
}

uint8_t LM75A_ReadTemperature(uint8_t addr, float *temp) {
    uint8_t read_data[2] = {0, 0};
    uint8_t write_data[1] = {0x00};
    int16_t received_data;
    
    if(addr < LM75A_ADDR_START || addr > LM75A_ADDR_END) {
        return 0;
    }
    
    I2C_WriteData(addr, write_data, 1);
    Delay_US(1);
    
    I2C_ReadData(addr, read_data, 2);
    received_data = (read_data[0] << 8) | read_data[1];
    
    if(received_data & 0x8000) {
        *temp = (float)((int16_t)received_data) / 256.0f;
    } else {
        *temp = (float)received_data / 256.0f;
    }
    
    return 1;
}

void LM75A_SetTos(uint8_t addr, float tos) {
    uint8_t write_buf[2];
    uint8_t tos_byte = (uint8_t)(tos * 2);
    
    write_buf[0] = LM75B_Tos;
    write_buf[1] = tos_byte;
    I2C_WriteData(addr, write_buf, 2);
}

void LM75A_SetThyst(uint8_t addr, float thyst) {
    uint8_t write_buf[2];
    uint8_t thyst_byte = (uint8_t)(thyst * 2);
    
    write_buf[0] = LM75B_Thyst;
    write_buf[1] = thyst_byte;
    I2C_WriteData(addr, write_buf, 2);
}

float LM75A_GetTos(uint8_t addr) {
    uint8_t read_buf[2];
    I2C_ReadData(addr, read_buf, 2);
    return (float)((read_buf[0] << 8) | read_buf[1]) / 256.0f;
}

float LM75A_GetThyst(uint8_t addr) {
    uint8_t read_buf[2];
    uint8_t reg = LM75B_Thyst;
    I2C_WriteData(addr, &reg, 1);
    I2C_ReadData(addr, read_buf, 2);
    return (float)((read_buf[0] << 8) | read_buf[1]) / 256.0f;
}