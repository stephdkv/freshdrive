(function ($) {
  $(document).ready(function () {
    // Добавляем контейнер для статуса после поля выбора транспорта
    var $transportField = $(".field-transport");
    $transportField.addClass("transport-select-wrapper");
    $transportField.append(
      '<div class="transport-status loading">Проверка доступности...</div>'
    );

    // Функция для обновления статуса транспорта
    function updateTransportStatus() {
      var $status = $(".transport-status");
      var transportId = $("#id_transport").val();
      var startDate = $("#id_rental_start_date").val();
      var endDate = $("#id_rental_end_date").val();
      var applicationId = window.location.pathname.split("/").slice(-2)[0];

      if (!transportId) {
        $status
          .removeClass("available unavailable loading")
          .addClass("loading")
          .html("Выберите транспорт");
        return;
      }

      if (!startDate || !endDate) {
        $status
          .removeClass("available unavailable loading")
          .addClass("loading")
          .html("Укажите даты аренды");
        return;
      }

      $status
        .removeClass("available unavailable")
        .addClass("loading")
        .html("Проверка доступности...");

      $.ajax({
        url: "/admin/check-transport-availability/",
        data: {
          transport_id: transportId,
          start_date: startDate,
          end_date: endDate,
          application_id: applicationId,
        },
        success: function (response) {
          $status.removeClass("loading");
          if (response.status.includes("✅")) {
            $status.addClass("available");
          } else {
            $status.addClass("unavailable");
          }
          $status.html(response.status);
        },
        error: function () {
          $status
            .removeClass("loading")
            .addClass("unavailable")
            .html("Ошибка проверки доступности");
        },
      });
    }

    // Обновляем статус при изменении транспорта или дат
    $("#id_transport, #id_rental_start_date, #id_rental_end_date").change(
      function () {
        updateTransportStatus();
      }
    );

    // Первоначальная проверка статуса
    updateTransportStatus();
  });
})(django.jQuery);
