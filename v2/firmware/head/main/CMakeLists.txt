set(root "${CMAKE_CURRENT_LIST_DIR}/../../..")
set(bmi "${root}/.work/bmi270")
idf_component_register(SRCS "main.cpp" "board.cpp" "interface.cpp" "network.cpp"
  "${root}/shared/face.cpp" "${root}/shared/motion.cpp" "${bmi}/bmi2.c" "${bmi}/bmi270.c"
  INCLUDE_DIRS "." "${root}/shared" "${bmi}"
  REQUIRES nvs_flash esp_wifi esp_event esp_netif esp_http_client esp_timer esp_driver_gpio esp_driver_i2c esp_driver_uart json)
target_compile_features(${COMPONENT_LIB} PRIVATE cxx_std_17)
