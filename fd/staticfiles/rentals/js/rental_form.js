(function ($) {
  $(document).ready(function () {
    console.log("Rental form JS loaded");

    // Проверяем наличие элементов формы
    const startDateField = $('input[name="rental_start_date"]');
    const endDateField = $('input[name="rental_end_date"]');
    const transportField = $('select[name="transport"]');

    console.log("Form elements found:", {
      startDate: startDateField.length > 0,
      endDate: endDateField.length > 0,
      transport: transportField.length > 0,
    });

    // Функция для форматирования даты в формат YYYY-MM-DD
    function formatDate(dateStr) {
      if (!dateStr) return null;

      // Пробуем разные форматы даты
      const formats = [
        { regex: /^(\d{2})\.(\d{2})\.(\d{4})$/, format: "$3-$2-$1" }, // DD.MM.YYYY
        { regex: /^(\d{4})-(\d{2})-(\d{2})$/, format: "$1-$2-$3" }, // YYYY-MM-DD
      ];

      for (let format of formats) {
        if (format.regex.test(dateStr)) {
          return dateStr.replace(format.regex, format.format);
        }
      }
      return null;
    }

    // Функция для обновления списка транспорта
    function updateTransportOptions() {
      console.log("updateTransportOptions called");

      // Получаем значения полей
      var startDateInput = startDateField.val();
      var endDateInput = endDateField.val();

      console.log("Raw dates:", startDateInput, endDateInput);

      var startDate = formatDate(startDateInput);
      var endDate = formatDate(endDateInput);

      console.log("Formatted dates:", startDate, endDate);

      if (!startDate || !endDate) {
        console.log("Both dates are required");
        return;
      }

      // Отправляем AJAX запрос
      console.log("Sending AJAX request with dates:", startDate, endDate);

      $.ajax({
        url: "/rentals/get-available-transport/",
        method: "GET",
        data: {
          start_date: startDate,
          end_date: endDate,
        },
        success: function (response) {
          console.log("Server response:", response);
          if (response.status === "success") {
            var $select = transportField;
            console.log(
              "Transport select element:",
              $select.length ? "found" : "not found"
            );

            // Сохраняем текущее выбранное значение
            var currentValue = $select.val();
            console.log("Current selected value:", currentValue);

            $select.empty();

            // Добавляем пустую опцию
            $select.append(
              $("<option>", {
                value: "",
                text: "---------",
              })
            );

            // Добавляем доступные транспортные средства
            response.options.forEach(function (option) {
              $select.append(
                $("<option>", {
                  value: option.id,
                  text: option.text,
                })
              );
            });

            // Пытаемся восстановить предыдущее значение, если оно доступно
            if (
              currentValue &&
              $select.find('option[value="' + currentValue + '"]').length > 0
            ) {
              $select.val(currentValue);
            }

            console.log("Transport options updated successfully");
          } else {
            console.log("Error in response:", response.message);
          }
        },
        error: function (xhr, status, error) {
          console.log("Ajax error:", status, error);
          console.log("Response text:", xhr.responseText);
        },
      });
    }

    // Функция для отслеживания изменений в полях даты
    function setupDateChangeTracking() {
      console.log("Setting up date change tracking");

      let lastStartDate = startDateField.val();
      let lastEndDate = endDateField.val();
      let updateTimeout;

      // Функция для проверки изменений
      function checkDateChanges() {
        const currentStartDate = startDateField.val();
        const currentEndDate = endDateField.val();

        if (
          currentStartDate !== lastStartDate ||
          currentEndDate !== lastEndDate
        ) {
          console.log("Date change detected:", {
            startDate: { from: lastStartDate, to: currentStartDate },
            endDate: { from: lastEndDate, to: currentEndDate },
          });

          lastStartDate = currentStartDate;
          lastEndDate = currentEndDate;

          clearTimeout(updateTimeout);
          updateTimeout = setTimeout(updateTransportOptions, 100);
        }
      }

      // Отслеживаем изменения каждые 100мс
      setInterval(checkDateChanges, 100);

      // Отслеживаем прямой ввод в поля
      startDateField.add(endDateField).on("input change", function () {
        console.log("Direct input detected:", this.name, this.value);
        lastStartDate = startDateField.val();
        lastEndDate = endDateField.val();
        clearTimeout(updateTimeout);
        updateTimeout = setTimeout(updateTransportOptions, 100);
      });

      // Проверяем начальные значения
      if (startDateField.val() && endDateField.val()) {
        console.log("Initial dates found, updating transport options");
        updateTransportOptions();
      }
    }

    // Инициализируем отслеживание изменений
    setupDateChangeTracking();

    // --- Автозаполнение данных клиента при выборе ---
    const clientField = $('select[name="client"]');
    const fullNameField = $('input[name="full_name"]');
    const phoneField = $('input[name="phone_number"]');
    const passportNumberField = $('input[name="passport_number"]');
    const passportIssuedByField = $('input[name="passport_issued_by"]');
    const passportIssueDateField = $('input[name="passport_issue_date"]');
    const howDidYouFindUsField = $('select[name="how_did_you_find_us"]');

    function autofillClientData(clientId) {
      if (!clientId) return;
      $.ajax({
        url: '/rentals/get-client-info/',
        method: 'GET',
        data: { client_id: clientId },
        success: function(response) {
          if (response.status === 'success' && response.data) {
            const data = response.data;
            if (fullNameField.length) fullNameField.val(data.full_name).trigger('change');
            if (phoneField.length) phoneField.val(data.phone_number).trigger('change');
            if (passportNumberField.length) passportNumberField.val(data.passport_number).trigger('change');
            if (passportIssuedByField.length) passportIssuedByField.val(data.passport_issued_by).trigger('change');
            if (passportIssueDateField.length) passportIssueDateField.val(data.passport_issue_date).trigger('change');
            if (howDidYouFindUsField.length && data.how_did_you_find_us) {
              howDidYouFindUsField.val(data.how_did_you_find_us).trigger('change');
            }
          }
        },
        error: function(xhr, status, error) {
          console.log('Ошибка при получении данных клиента:', status, error);
        }
      });
    }

    if (clientField.length) {
      clientField.on('change', function() {
        const clientId = $(this).val();
        autofillClientData(clientId);
      });
    }
  });
})(django.jQuery);
