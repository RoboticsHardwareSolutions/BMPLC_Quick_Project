import logging
import sys
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

# Поддержка встроенного парсера TOML
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class TestbenchController:
    def __init__(self, config_path="testbench.toml"):
        # Загрузка конфигурации из файла
        with open(config_path, "rb") as f:
            self.config = tomllib.load(f)["io"]

        self.conn = self.config["connection"]

        # Инициализация Modbus RTU клиента
        self.client = ModbusSerialClient(
            port=self.conn["port"],
            baudrate=self.conn["baudrate"],
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=self.conn["timeout"]
        )

    def connect(self) -> bool:
        if not self.client.connect():
            logger.error(f"Не удалось открыть последовательный порт: {self.conn['port']}")
            return False
        logger.info(f"Порт {self.conn['port']} успешно открыт.")
        return True

    def close(self):
        self.client.close()
        logger.info("Соединение с портом закрыто.")

    def read_inputs(self) -> dict | None:
        """Читает Holding регистры входов и разбирает их на именованные биты."""
        reg_map = self.config["map"]["inputs"]
        slave_id = self.conn["inputs_id"]  # ID для блока входов из [io.connection]

        if reg_map["register_type"] != "holding":
            logger.error("Ошибка конфигурации: ожидался тип 'holding' для секции inputs.")
            return None

        try:
            # Чтение последовательности 16-битных регистров
            response = self.client.read_holding_registers(
                address=reg_map["start_address"],
                count=reg_map["count"],
                slave=slave_id
            )

            if response.isError():
                logger.error(f"Modbus ошибка чтения входов (Slave {slave_id}): {response}")
                return None

            # Склеиваем список 16-битных регистров в единую битовую маску
            combined_bits = 0
            for i, reg_value in enumerate(response.registers):
                combined_bits |= (reg_value << (i * 16))

            # Разбор маски по именованным битам
            results = {}
            for bit_str, label in reg_map["labels"].items():
                bit_idx = int(bit_str)
                bit_value = (combined_bits >> bit_idx) & 1
                results[label] = bool(bit_value)

            return results

        except ModbusException as e:
            logger.error(f"Исключение Modbus при чтении входов: {e}")
            return None

    def write_output_by_label(self, target_label: str, state: bool) -> bool:
        """Находит физический адрес Coil по имени метки и отправляет команду записи."""
        reg_map = self.config["map"]["outputs"]
        slave_id = self.conn["ouputs_id"]  # Учитываем опечатку в ключе 'ouputs_id'

        if reg_map["register_type"] != "coil":
            logger.error("Ошибка конфигурации: ожидался тип 'coil' для секции outputs.")
            return False

        # Поиск адреса регистра по текстовой метке
        target_address = None
        for addr_str, label in reg_map["labels"].items():
            if label == target_label:
                target_address = int(addr_str)
                break

        if target_address is None:
            logger.error(f"Метка выхода '{target_label}' не найдена в конфигурации TOML.")
            return False

        try:
            logger.info(f"Управление выходом: {target_label} (Coil {target_address}) -> {'ВКЛ' if state else 'ВЫКЛ'}")
            response = self.client.write_coil(
                address=target_address,
                value=state,
                slave=slave_id
            )

            if response.isError():
                logger.error(f"Modbus ошибка записи выхода (Slave {slave_id}, Coil {target_address}): {response}")
                return False
            return True

        except ModbusException as e:
            logger.error(f"Исключение Modbus при записи выхода: {e}")
            return False


if __name__ == "__main__":
    # Демонстрационный цикл проверки стенда
    tb = TestbenchController()

    if tb.connect():
        try:
            # 1. Чтение и маппинг входов
            print("\n=== Статус кнопок и выходов PLC ===")
            states = tb.read_inputs()
            if states:
                for label, is_active in states.items():
                    print(f" {label.ljust(15)} : {'[ ПИТАНИЕ / СИГНАЛ ]' if is_active else '[ ОТКЛЮЧЕНО ]'}")

            print("\n=== Тестовая коммутация стенда ===")
            # 2. Включаем питание ПЛК и пробрасываем USB-каналы хаба
            tb.write_output_by_label("PWR_PLC_XL", True)
            tb.write_output_by_label("USB_PLC_XL", True)

        except KeyboardInterrupt:
            logger.info("Выполнение прервано пользователем.")
        finally:
            tb.close()
