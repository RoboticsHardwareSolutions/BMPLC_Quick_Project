- проверить результат тестов многократных в корне проекта 
- __FILE__ of rhs_assert / runit relative to the repo: shorter strings in the flash  add_compile_options(-fmacro-prefix-map=${CMAKE_SOURCE_DIR}/=)

- rhs_hal_i2c.c это ад летящий на крыльях ночи надо что то придумать с инициализацией GPIO
- создать отдельный workflow hil
- добавить rlibhelper и отформатировать весь код 
- переделать стили страницы с IO 
- заменить все вызовы где уместно с printf на RLOG это создаст гарантированно потокобезопасный вывод данных что важно для проведения тестов ! когда вывод может быть нарущен
- Если в сабмодулях есть diff то писать это при выводе
- Удалить old_gpio ото всюду после завершения покрытия тестами 
- set(RHS_TEST_EEPROM OFF) - для XL выключен и не проверен ! 
- удалить deprecated option из rhs.cmake 

  Режим Bridge на остальных интерфейсах/платах на реальных устройствах проверим позже на стенде:
  - can Bridge на G0B1 (FDCAN1 PB8/PB9) с адаптером стенда [iface.canbus]
  - драйвер rhs_hal_can_fdcan.c для G0B1: прием/передача, IRQ TIM16_FDCAN_IT0, SCE (bus-off, error passive), битрейты от PCLK1
  - rs232/rs485 Bridge на XL и M с адаптерами [iface.rs232] / [iface.rs485], смена baud из line coding хоста —


запусти полный набор тестов 5 раз с сохраниением результата в файл в корне проекта 






- 


  



