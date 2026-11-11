- создать отдельный workflow hil
- добавить rlibhelper и отформатировать весь код 
- переделать стили страницы с IO 
- перенести скрипты линкера в отдельные директории
- В папке toolchain задублированный код !
- заменить все вызовы где уместно с printf на RLOG это создаст гарантированно потокобезопасный вывод данных что важно для проведения тестов ! когда вывод может быть нарущен
- Если в сабмодулях есть diff то писать это при выводе
- Net не добавлен как сервис а сразу впилен отклбчить его нельзя надо сделать как сервис
- Удалить old_gpio ото всюду после завершения покрытия тестами 
- RHS_HAL_I2C реализовать через BSP EEPROM других поводов включать I2C нет 
- set(RHS_TEST_EEPROM OFF) - для XL выключен и не проверен ! 
- удалить deprecated option из rhs.cmake 
- usb_bridge: режим App для can и rs232/rs485, CLI `usb` и сообщения о неподдерживаемых режимах проверены на всех платах
  (user_tests/usb_bridge_test/testbench): G0B1 на столе 67/67, HIL XL 63 + 1 skip, HIL M 66/66; slcan_test 145/0.
  Режим Bridge на реальных устройствах проверим позже на стенде:
  - can Bridge на XL (bxCAN1 PD0/PD1, PG10=high) и G0B1 (FDCAN1 PB8/PB9) с адаптером стенда [iface.canbus] (DN0536AY)
  - драйвер rhs_hal_can_fdcan.c для G0B1: прием/передача, IRQ TIM16_FDCAN_IT0, SCE (bus-off, error passive), битрейты от PCLK1
  - rs232/rs485 Bridge на XL и M с адаптерами [iface.rs232] / [iface.rs485], смена baud из line coding хоста
  - eth во всех режимах на XL после переноса из net/usb_eth_bridge; тест eth App не написан (нужны raw L2-кадры на хосте)
  - режим BridgeApp для всех целей
  - HIL-тесты Bridge с адаптерами стенда не написаны
  - на XL при PG10=low старт должен давать ошибку "USB is not available"
  - frontend /api/bridges на usb_bridge
  - совместимость с Linux slcand / SocketCAN
- HIL-стенд (gasystems@192.168.221.6): нет интернета — python-can/pyserial ставились колёсами офлайн в копию .venv
  (~/projects/BMPLC_usb_bridge_hil); в рабочей копии стенда ~/projects/BMPLC_Quick_Project их нет
- HIL-стенд: демон io_hub, запущенный фикстурой, на первый set_coils отвечает ошибкой (status 1); с заранее
  запущенным демоном (testbench -d) всё работает — разобраться
