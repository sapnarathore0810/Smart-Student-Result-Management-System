/*
  Client-side helpers for the result portal.
  The server still performs all validation, so this file only improves UX.
*/

document.addEventListener('DOMContentLoaded', function () {
  var form = document.getElementById('studentForm');

  if (!form) {
    return;
  }

  var nameInput = document.getElementById('student_name');
  var rollInput = document.getElementById('roll_number');
  var subjectInputs = [
    document.getElementById('subject1'),
    document.getElementById('subject2'),
    document.getElementById('subject3')
  ];

  var previewName = document.getElementById('previewName');
  var previewRoll = document.getElementById('previewRoll');
  var previewTotal = document.getElementById('previewTotal');
  var previewPercentage = document.getElementById('previewPercentage');
  var previewGrade = document.getElementById('previewGrade');
  var previewStatus = document.getElementById('previewStatus');

  function calculateGrade(percentage) {
    if (percentage >= 75) {
      return 'A';
    }

    if (percentage >= 50) {
      return 'B';
    }

    return 'C';
  }

  function calculateStatus(percentage) {
    return percentage >= 40 ? 'Pass' : 'Fail';
  }

  function toNumber(input) {
    var value = Number(input.value);
    return Number.isFinite(value) ? value : 0;
  }

  function updatePreview() {
    var total = subjectInputs.reduce(function (sum, input) {
      return sum + toNumber(input);
    }, 0);
    var percentage = total ? (total / 300) * 100 : 0;

    previewName.textContent = nameInput.value.trim() || '-';
    previewRoll.textContent = rollInput.value.trim() || '-';
    previewTotal.textContent = String(total);
    previewPercentage.textContent = percentage.toFixed(2) + '%';
    previewGrade.textContent = calculateGrade(percentage);
    previewStatus.textContent = calculateStatus(percentage);
  }

  function validateForm(event) {
    var errors = [];

    if (!nameInput.value.trim()) {
      errors.push('Student name is required.');
    }

    if (!rollInput.value.trim()) {
      errors.push('Roll number is required.');
    }

    subjectInputs.forEach(function (input, index) {
      var rawValue = input.value.trim();
      var mark = Number(rawValue);

      if (!rawValue) {
        errors.push('Subject ' + (index + 1) + ' marks are required.');
        return;
      }

      if (!Number.isFinite(mark) || mark < 0 || mark > 100) {
        errors.push('Subject ' + (index + 1) + ' marks must be between 0 and 100.');
      }
    });

    if (errors.length > 0) {
      event.preventDefault();
      alert(errors.join('\n'));
    }
  }

  form.addEventListener('submit', validateForm);

  [nameInput, rollInput].concat(subjectInputs).forEach(function (input) {
    input.addEventListener('input', updatePreview);
  });

  updatePreview();
});
