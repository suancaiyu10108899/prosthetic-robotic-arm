#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEClient.h>

static BLEAddress targetAddress("D5:51:FA:B6:09:71"); // 目标设备的 MAC 地址
static bool isConnected = false;
static BLEClient* pClient = nullptr;

// Service / Characteristic UUID
static BLEUUID serviceUUID("0000AE30-0000-1000-8000-00805F9B34FB");
static BLEUUID charUUID("0000AE02-0000-1000-8000-00805F9B34FB");

class MyClientCallback : public BLEClientCallbacks {
  void onConnect(BLEClient* pclient) {
    Serial.println("****************************************");
    Serial.print("已连接到设备: ");
    Serial.println(targetAddress.toString().c_str());
    isConnected = true;
  }

  void onDisconnect(BLEClient* pclient) {
    Serial.println("****************************************");
    Serial.println("设备已断开");
    isConnected = false;
  }
};

// Notify 回调函数
void notifyCallback(
  BLERemoteCharacteristic* pBLERemoteCharacteristic,
  uint8_t* pData,
  size_t length,
  bool isNotify) {

  Serial.println("****************************************");
  Serial.print(targetAddress.toString().c_str());
  Serial.print("\n收到通知数据: ");
  for (size_t i = 0; i < length; i++) {
    if (pData[i] < 16) Serial.print("0");
    Serial.print(pData[i], HEX);
  }
  Serial.println();
}

// 连接并订阅通知
void connectToServer() {
  Serial.print("尝试连接到: ");
  Serial.println(targetAddress.toString().c_str());

  pClient = BLEDevice::createClient();
  pClient->setClientCallbacks(new MyClientCallback());

  if (!pClient->connect(targetAddress)) {
    Serial.println("连接失败!");
    return;
  }

  BLERemoteService* pRemoteService = pClient->getService(serviceUUID);
  if (pRemoteService == nullptr) {
    Serial.println("找不到 Service, 断开连接");
    pClient->disconnect();
    return;
  }

  BLERemoteCharacteristic* pRemoteCharacteristic = pRemoteService->getCharacteristic(charUUID);
  if (pRemoteCharacteristic == nullptr) {
    Serial.println("找不到 Characteristic, 断开连接");
    pClient->disconnect();
    return;
  }

  if (pRemoteCharacteristic->canNotify()) {
    pRemoteCharacteristic->registerForNotify(notifyCallback);
    Serial.println("已注册通知回调");
  } else {
    Serial.println("该特征不支持 Notify");
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("启动 BLE 客户端...");
  BLEDevice::init("");
}

void loop() {
  if (!isConnected) {
    connectToServer();
  }
  delay(5000);
}
