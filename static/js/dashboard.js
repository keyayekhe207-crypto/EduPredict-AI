/*
 * static/js/dashboard.js
 * ------------------------
 * Reads the JSON data Flask embedded in #dashboard-data and renders
 * the four dashboard charts using the shared builders in charts.js.
 */

document.addEventListener("DOMContentLoaded", function () {
  var dataEl = document.getElementById("dashboard-data");
  if (!dataEl || !window.EduCharts) return;

  var data = JSON.parse(dataEl.textContent);

  EduCharts.renderPerformanceDoughnut("performanceChart", data.performanceDistribution);
  EduCharts.renderSubjectBar("subjectChart", data.subjectAverages);
  EduCharts.renderAttendanceBar("attendanceChart", data.attendanceBuckets);
  EduCharts.renderStudyHoursBar("studyHoursChart", data.studyHoursVsPerformance);
});
