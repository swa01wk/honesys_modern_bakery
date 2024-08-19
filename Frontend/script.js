let filterAPIResponse = [];
let transformAPIResponse = [];
let forecastAPIResponse = [];

// Helper function to show/hide loaders
function showLoader(loaderId) {
  document.getElementById(loaderId).classList.remove("hidden");
}

function hideLoader(loaderId) {
  document.getElementById(loaderId).classList.add("hidden");
}

document.getElementById("filterButton").addEventListener("click", function () {
  const apiUrl = "http://127.0.0.1:5000/filter_data";

  const data = {
    file_path: document.getElementById("file_path").value,
    material_name: document.getElementById("material_name").value,
    sold_to_party: parseInt(document.getElementById("sold_to_party").value, 10),
  };

  showLoader("filter-loader");

  fetch(apiUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  })
    .then((response) => response.json())
    .then((data) => {
      filterAPIResponse = data;
      const container = document.getElementById("filter-card-container");
      container.innerHTML = ""; // Clear previous content

      data.forEach((item) => {
        const card = document.createElement("div");
        card.className = "card";

        card.innerHTML = `
          <div class="card-title"><b>Material Name :</b> ${
            item.MaterialName
          }</div>
          <div class="card-content"><b>Material :</b> ${item.Material}</div>
          <div class="card-content"><b>Base Unit :</b> ${item.BaseUnit}</div>
          <div class="card-content"><b>Billing Document Type :</b> ${
            item.BillingDocumentType
          }</div>
          <div class="card-content"><b>Billing Date :</b> ${new Date(
            item.BillingDate
          ).toLocaleDateString()}</div>
          <div class="card-content"><b>Net Sales :</b> ${
            item["Net Sales"]
          }</div>
          <div class="card-content"><b>Plant :</b> ${item.Plant}</div>
          <div class="card-content"><b>Quantity In Base Unit :</b> ${
            item.QuantityInBaseUnit
          }</div>
          <div class="card-content"><b>Region :</b> ${item.Region}</div>
          <div class="card-content"><b>Sold To Party :</b> ${
            item.SoldToParty
          }</div>
        `;
        container.appendChild(card);
      });
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("An error occurred while fetching filtered data: " + error);
    })
    .finally(() => {
      hideLoader("filter-loader");
    });
});

// Transform Data
document
  .getElementById("transformButton")
  .addEventListener("click", function () {
    const apiUrl = "http://127.0.0.1:5000/transform_data";

    const data = {
      filtered_data: filterAPIResponse,
    };

    showLoader("transform-loader");

    fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })
      .then((response) => response.json())
      .then((data) => {
        transformAPIResponse = data;
        const container = document.getElementById("transform-card-container");
        container.innerHTML = ""; // Clear previous content

        data.forEach((item) => {
          const card = document.createElement("div");
          card.className = "card";

          card.innerHTML = `
          <div class="card-title"><b>Material Name :</b> ${item.MaterialName}</div>
          <div class="card-content"><b>Billing Date :</b> ${item.BillingDate}</div>
          <div class="card-content"><b>Expired_sum :</b> ${item.expired_sum}</div>
          <div class="card-content"><b>Shelved_sum :</b> ${item.shelved_sum}</div>
        `;
          container.appendChild(card);
        });
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred while transforming data: " + error);
      })
      .finally(() => {
        hideLoader("transform-loader");
      });
  });

// Forecast Data
document
  .getElementById("forecastButton")
  .addEventListener("click", function () {
    const apiUrl = "http://127.0.0.1:5000/forecast";

    const data = {
      aggregated_data: transformAPIResponse,
    };

    showLoader("forecast-loader");

    fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })
      .then((response) => response.json())
      .then((data) => {
        forecastAPIResponse = data;
        const container = document.getElementById("forecast-card-container");
        container.innerHTML = ""; // Clear previous content

        data.forEach((item) => {
          const card = document.createElement("div");
          card.className = "card";

          card.innerHTML = `

          <div class="card-content"><b>Forecast Net :</b> ${item.forecast_net}</div>
        `;
          container.appendChild(card);
        });
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred while forecasting data: " + error);
      })
      .finally(() => {
        hideLoader("forecast-loader");
      });
  });
