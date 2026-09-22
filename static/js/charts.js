/*
 * static/js/charts.js
 * --------------------
 * Small, reusable Chart.js builders shared by dashboard.js, analysis.html
 * and student_details.html. Keeping chart construction in one place
 * means every page uses the same colors and styling automatically.
 */

(function () {
  "use strict";

  var COLORS = {
    primary: "#2F5D8A",
    primaryLight: "#8FB0CD",
    ink: "#5B6472",
    grid: "#E1E5EB",
    good: "#2E8B57",
    average: "#C98A1D",
    risk: "#C0392B",
  };

  Chart.defaults.font.family = "'Inter', 'Segoe UI', sans-serif";
  Chart.defaults.color = COLORS.ink;
  Chart.defaults.plugins.legend.labels.boxWidth = 10;
  Chart.defaults.plugins.legend.labels.boxHeight = 10;

  function baseGrid() {
    return {
      color: COLORS.grid,
      drawTicks: false,
    };
  }

  /** Doughnut chart for At Risk / Average / Good counts. */
  function renderPerformanceDoughnut(canvasId, dist) {
    var el = document.getElementById(canvasId);
    if (!el) return null;
    var labels = ["At Risk", "Average", "Good"];
    var values = labels.map(function (l) { return dist[l] || 0; });

    return new Chart(el.getContext("2d"), {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: [COLORS.risk, COLORS.average, COLORS.good],
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        cutout: "68%",
        plugins: {
          legend: { position: "bottom" },
        },
      },
    });
  }

  /** Bar chart of average marks per subject. */
  function renderSubjectBar(canvasId, subjectAverages) {
    var el = document.getElementById(canvasId);
    if (!el) return null;
    var labels = Object.keys(subjectAverages);
    var values = labels.map(function (k) { return subjectAverages[k]; });

    return new Chart(el.getContext("2d"), {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Average marks (%)",
          data: values,
          backgroundColor: COLORS.primary,
          borderRadius: 6,
          maxBarThickness: 42,
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, max: 100, grid: baseGrid() },
          x: { grid: { display: false } },
        },
      },
    });
  }

  /** Bar chart of attendance distribution buckets. */
  function renderAttendanceBar(canvasId, buckets) {
    var el = document.getElementById(canvasId);
    if (!el) return null;
    var labels = Object.keys(buckets);
    var values = labels.map(function (k) { return buckets[k]; });

    return new Chart(el.getContext("2d"), {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Students",
          data: values,
          backgroundColor: COLORS.primaryLight,
          borderRadius: 6,
          maxBarThickness: 52,
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 }, grid: baseGrid() },
          x: { grid: { display: false } },
        },
      },
    });
  }

  /** Bar chart: average study hours per performance category. */
  function renderStudyHoursBar(canvasId, studyVsPerf) {
    var el = document.getElementById(canvasId);
    if (!el) return null;
    var labels = Object.keys(studyVsPerf);
    var values = labels.map(function (k) { return studyVsPerf[k]; });
    var colors = labels.map(function (l) {
      if (l === "At Risk") return COLORS.risk;
      if (l === "Average") return COLORS.average;
      return COLORS.good;
    });

    return new Chart(el.getContext("2d"), {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Avg. study hours/day",
          data: values,
          backgroundColor: colors,
          borderRadius: 6,
          maxBarThickness: 60,
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: baseGrid() },
          x: { grid: { display: false } },
        },
      },
    });
  }

  /** Doughnut chart for Low/Medium/High risk-level counts. */
  function renderRiskDoughnut(canvasId, riskDist) {
    var el = document.getElementById(canvasId);
    if (!el) return null;
    var labels = ["Low Risk", "Medium Risk", "High Risk"];
    var values = labels.map(function (l) { return riskDist[l] || 0; });

    return new Chart(el.getContext("2d"), {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: [COLORS.good, COLORS.average, COLORS.risk],
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        cutout: "68%",
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  /** Small bar chart of one student's estimated subject marks. */
  function renderSubjectBreakdown(canvasId, breakdown) {
    var el = document.getElementById(canvasId);
    if (!el) return null;
    var labels = Object.keys(breakdown);
    var values = labels.map(function (k) { return breakdown[k]; });

    return new Chart(el.getContext("2d"), {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Marks (%)",
          data: values,
          backgroundColor: COLORS.primary,
          borderRadius: 6,
          maxBarThickness: 34,
        }],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, max: 100, grid: baseGrid() },
          y: { grid: { display: false } },
        },
      },
    });
  }

  window.EduCharts = {
    colors: COLORS,
    renderPerformanceDoughnut: renderPerformanceDoughnut,
    renderSubjectBar: renderSubjectBar,
    renderAttendanceBar: renderAttendanceBar,
    renderStudyHoursBar: renderStudyHoursBar,
    renderRiskDoughnut: renderRiskDoughnut,
    renderSubjectBreakdown: renderSubjectBreakdown,
  };
})();
