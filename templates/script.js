let filterAPIResponse = [];
let transformAPIResponse = [];
let forecastAPIResponse = [];

const BASE_PATH = "http://43.204.211.22:5000";
/* const BASE_PATH = "http://127.0.0.1:5000"; */

document.addEventListener("DOMContentLoaded", function () {
  // Disable buttons initially
  document.getElementById("filterButton").disabled = true;
  document.getElementById("transformButton").disabled = true;
  document.getElementById("forecastButton").disabled = true;

  // Fetch materials
  const materialApiUrl = `${BASE_PATH}/all_materials`;
  fetch(materialApiUrl)
    .then((response) => response.json())
    .then((data) => {
      const materialDropdown = document.getElementById("material_name");
      data.forEach((material) => {
        const option = document.createElement("option");
        option.value = material;
        option.text = material;
        materialDropdown.appendChild(option);
      });
    })
    .catch((error) => {
      console.error("Error fetching materials:", error);
    });

  // Fetch vendors
  const vendorApiUrl = `${BASE_PATH}/all_vendors`;
  fetch(vendorApiUrl)
    .then((response) => response.json())
    .then((data) => {
      const soldToPartyDropdown = document.getElementById("sold_to_party");
      data.forEach((party) => {
        const option = document.createElement("option");
        option.value = party;
        option.text = party;
        soldToPartyDropdown.appendChild(option);
      });
    })
    .catch((error) => {
      console.error("Error fetching vendors:", error);
    });

  // Handle filter button click
  document
    .getElementById("filterButton")
    .addEventListener("click", function () {
      const material = document.getElementById("material_name").value;
      const soldToParty = document.getElementById("sold_to_party").value;

      // Check if both dropdowns are selected
      if (!material || !soldToParty) {
        alert(
          "Please select both Material Name and Sold to Party before filtering."
        );
        return;
      }

      const apiUrl = `${BASE_PATH}/filter_data`;
      const data = {
        material_name: material,
        sold_to_party: parseInt(soldToParty),
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
          container.innerHTML = ""; 

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

          if (filterAPIResponse.length > 0) {
            document.getElementById("transformButton").disabled = false;
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("An error occurred while fetching filtered data: " + error);
        })
        .finally(() => {
          hideLoader("filter-loader");
        });
    });
});

function showLoader(loaderId) {
  document.getElementById(loaderId).classList.remove("hidden");
}

function hideLoader(loaderId) {
  document.getElementById(loaderId).classList.add("hidden");
}

// Load data
document
  .getElementById("loadDataButton")
  .addEventListener("click", function () {
    const apiUrl = `${BASE_PATH}/load_data`;

    showLoader("data-loader");

    fetch(apiUrl)
      .then((response) => response.json())
      .then((data) => {
        if (data.status === true) {
          document.getElementById("filterButton").disabled = false;
        } else {
          alert("Data loading failed. Try again.");
        }
        hideLoader("data-loader");
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred while loading data: " + error);
      });
  });

// Transform data
document
  .getElementById("transformButton")
  .addEventListener("click", function () {
    const apiUrl = `${BASE_PATH}/transform_data`;
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
        container.innerHTML = "";

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

        if (transformAPIResponse.length > 0) {
          document.getElementById("forecastButton").disabled = false;
        }
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
    const apiUrl = `${BASE_PATH}/forecast`;
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
        const container = document.getElementById("forecast-card-container");
        container.innerHTML = ""; 

        // Display image
        const imageUrl = `${BASE_PATH}${data.image_url}`;
        const image = document.createElement("img");
        image.src = imageUrl;
        image.alt = "Forecast Image";
        image.className = "forecast-image";
        container.appendChild(image);

        const forecastMaincontent = document.createElement("div");
        forecastMaincontent.className = "forecastMaincontent";
        container.appendChild(forecastMaincontent);
        // Display forecasted expired data
        const expiredContainer = document.createElement("div");
        expiredContainer.className = "expiredContainer";
        expiredContainer.innerHTML = "<b>Forecasted Expiry</b>";
        data.forecasted_expired.forEach((item) => {
          const card = document.createElement("div");
          card.className = "cardContainer";
          card.innerHTML = `
            <div class="card-title"><b>Forecast expired sum :</b> ${item.forecast_expired_sum}</div>
          `;
          expiredContainer.appendChild(card);
        });
        forecastMaincontent.appendChild(expiredContainer);

        // Display forecasted net data
        const netContainer = document.createElement("div");
        netContainer.className = "netContainer";
        netContainer.innerHTML = "<b>Forecasted Net</b>";
        data.forecasted_net.forEach((item) => {
          const card = document.createElement("div");
          card.className = "cardContainer";
          card.innerHTML = `
            <div class="card-title"><b>Forecast net :</b> ${item.forecast_net}</div>
          `;
          netContainer.appendChild(card);
        });
        forecastMaincontent.appendChild(netContainer);

        // Display forecasted shelved data
        const shelvedContainer = document.createElement("div");
        shelvedContainer.className = "shelvedContainer";
        shelvedContainer.innerHTML = "<b>Forecasted Shelved</b>";
        data.forecasted_shelved.forEach((item) => {
          const card = document.createElement("div");
          card.className = "cardContainer";
          card.innerHTML = `
            <div class="card-title"><b>Forecast shelved sum :</b> ${item.forecast_shelved_sum}</div>
          `;
          shelvedContainer.appendChild(card);
        });
        forecastMaincontent.appendChild(shelvedContainer);
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred while forecasting data: " + error);
      })
      .finally(() => {
        hideLoader("forecast-loader");
      });
  });
