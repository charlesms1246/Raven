document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("search-input");
    const searchButton = document.getElementById("search-button");
    const videoFeed = document.querySelector(".video-feed");
    const objectsList = document.querySelector(".objects-list");
    const barChartCanvas = document.getElementById("barChart").getContext("2d");
    const pieChartCanvas = document.getElementById("pieChart").getContext("2d");

    let barChart, pieChart;
    let detectionCounts = {};

    /** 🔍 SEARCH CCTV BY ID & UPDATE VIDEO FEED **/
    searchButton.addEventListener("click", function () {
        const cctvId = searchInput.value.trim();
        if (cctvId === "") return;

        fetch(`/get_camera_info/${cctvId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("Camera not found!");
                } else {
                    videoFeed.src = data.v_link;  // Update video feed
                    updateOfficerDetails(data);
                }
            })
            .catch(error => console.error("Error fetching camera info:", error));
    });

    /** 🎥 UPDATE OFFICER & CCTV DETAILS **/
    function updateOfficerDetails(data) {
        document.getElementById("cctv_id").textContent = data.cctv_id;
        document.getElementById("cctv_location").textContent = data.address;
        document.getElementById("officer_name").textContent = data.officer_name;
        document.getElementById("officer_post").textContent = data.officer_post;
        document.getElementById("officer_phone").textContent = data.officer_phone;
        document.getElementById("cctv_channel").textContent = data.channel;
    }

    /** 📡 FETCH DETECTION UPDATES EVERY 5 SECONDS **/
    setInterval(() => {
        fetch("/get_latest_detection")
            .then(response => response.json())
            .then(data => {
                if (data.cctv_id) {
                    fetch(`/get_camera_info/${data.cctv_id}`)
                        .then(response => response.json())
                        .then(cameraData => {
                            videoFeed.src = cameraData.v_link;  // Update live feed
                            updateOfficerDetails(cameraData);
                        });
                }
            })
            .catch(error => console.error("Error fetching latest detection:", error));

        updateDetectionSummary();
    }, 5000);

    /** 📊 FETCH OBJECT DETECTION SUMMARY & UPDATE UI **/
    function updateDetectionSummary() {
        fetch("/get_latest_detection")
            .then(response => response.json())
            .then(data => {
                if (!data.cctv_id) return;

                fetch(`/camera_feed/${data.cctv_id}`)
                    .then(response => response.json())
                    .then(detectionData => {
                        objectsList.innerHTML = ""; // Clear previous detections
                        detectionCounts = {}; // Reset detection count

                        detectionData.forEach(detection => {
                            const li = document.createElement("li");
                            li.textContent = `${detection.label} (${detection.confidence * 100}%)`;
                            objectsList.appendChild(li);

                            // Update detection count for charts
                            detectionCounts[detection.label] = (detectionCounts[detection.label] || 0) + 1;
                        });

                        updateCharts(); // Update graphs dynamically
                    });
            })
            .catch(error => console.error("Error fetching detection summary:", error));
    }

    /** 📊 UPDATE BAR & PIE CHARTS **/
    function updateCharts() {
        const labels = Object.keys(detectionCounts);
        const dataValues = Object.values(detectionCounts);

        // 🟦 Bar Chart
        if (barChart) barChart.destroy();
        barChart = new Chart(barChartCanvas, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Detected Objects",
                    data: dataValues,
                    backgroundColor: "rgba(54, 162, 235, 0.6)",
                    borderColor: "rgba(54, 162, 235, 1)",
                    borderWidth: 1
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        // 🟠 Pie Chart
        if (pieChart) pieChart.destroy();
        pieChart = new Chart(pieChartCanvas, {
            type: "pie",
            data: {
                labels: labels,
                datasets: [{
                    data: dataValues,
                    backgroundColor: ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF"]
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }
});
