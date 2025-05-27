(function ($) {
  $(document).ready(function () {
    // Добавляем контейнер для статуса после поля выбора транспорта
    var $transportField = $(".field-transport");
    if ($transportField.length) {
      $transportField.append(
        '<div class="availability-status loading">Выберите транспорт и даты аренды</div>'
      );
    }

    // Функция для проверки доступности
    function checkAvailability() {
      var $status = $(".availability-status");
      var transportId = $("#id_transport").val();
      var startDate = $("#id_rental_start_date").val();
      var endDate = $("#id_rental_end_date").val();

      // Получаем ID заявки из URL если это редактирование
      var applicationId = window.location.pathname
        .split("/")
        .filter(Boolean)
        .pop();
      if (isNaN(applicationId)) {
        applicationId = null;
      }

      // Проверяем, что все поля заполнены
      if (!transportId || !startDate || !endDate) {
        $status
          .removeClass("available unavailable")
          .addClass("loading")
          .text("Выберите транспорт и даты аренды");
        return;
      }

      // Показываем статус загрузки
      $status
        .removeClass("available unavailable")
        .addClass("loading")
        .text("Проверка доступности...");

      // Отправляем запрос на сервер
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
          if (response.status === "success") {
            if (response.is_available) {
              $status
                .removeClass("unavailable")
                .addClass("available")
                .text(response.message);
            } else {
              $status
                .removeClass("available")
                .addClass("unavailable")
                .text(response.message);
            }
          } else {
            $status
              .removeClass("available")
              .addClass("unavailable")
              .text(response.message);
          }
        },
        error: function () {
          $status
            .removeClass("loading available")
            .addClass("unavailable")
            .text("Ошибка при проверке доступности");
        },
      });
    }

    // Добавляем обработчики событий
    $("#id_transport, #id_rental_start_date, #id_rental_end_date").change(
      function () {
        checkAvailability();
      }
    );

    // Проверяем доступность при загрузке страницы
    if ($("#id_transport").val()) {
      setTimeout(checkAvailability, 500);
    }
  });
})(django.jQuery);
