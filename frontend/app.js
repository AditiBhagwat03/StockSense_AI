document.addEventListener("DOMContentLoaded", () => {
    console.log("STOCKSENSE AI frontend loaded.");
    loadDashboard();
    setupCopilot();
});


async function loadDashboard() {
    try {
        const response = await fetch("/api/dashboard");

        if (!response.ok) {
            throw new Error(`Dashboard request failed: ${response.status}`);
        }

        const data = await response.json();

        if (data.status !== "success") {
            throw new Error("Dashboard data could not be loaded.");
        }

        document.getElementById("total-products").textContent =
            data.total_products;

        document.getElementById("low-stock").textContent =
            data.low_stock_count;

        document.getElementById("overstock").textContent =
            data.overstock_count;

        document.getElementById("sales-changes").textContent =
            data.sales_changes_count;

        renderStockoutRisks(data.stockout);
        renderSalesChanges(data.sales_changes);
        renderPriorities(data.priorities);

        console.log("Dashboard data loaded successfully.");

    } catch (error) {
        console.error("Dashboard loading error:", error);

        document.getElementById("total-products").textContent = "--";
        document.getElementById("low-stock").textContent = "--";
        document.getElementById("overstock").textContent = "--";
        document.getElementById("sales-changes").textContent = "--";

        showDashboardError("Unable to load verified retail data.");
    }
}


function renderStockoutRisks(items) {
    const container = document.getElementById("stockout-list");

    if (!items || items.length === 0) {
        container.innerHTML = "<p>No current stock-out risks.</p>";
        return;
    }

    container.innerHTML = items.map(item => {

        const riskClass =
            item.risk_level.toLowerCase().replace(" ", "-");

        const actionMessage =
            item.review_message ||
            (item.risk_level === "HIGH"
                ? "Immediate replenishment review"
                : "Monitor and review replenishment");

        return `
            <div class="stockout-card">

                <div class="stockout-top">

                    <div>
                        <h4>${item.product_id} — ${item.product_name}</h4>
                        <p class="store-name">${item.store_name}</p>
                    </div>

                    <span class="risk-badge ${riskClass}">
                        ${item.risk_level} RISK
                    </span>

                </div>

                <div class="stockout-metrics">

                    <div class="stockout-metric">
                        <span>Current Stock</span>
                        <strong>${item.current_stock} units</strong>
                    </div>

                    <div class="stockout-metric">
                        <span>Daily Sales</span>
                        <strong>${Number(item.average_daily_sales).toFixed(1)} units</strong>
                    </div>

                    <div class="stockout-metric">
                        <span>Days of Cover</span>
                        <strong>${Number(item.days_of_cover).toFixed(1)} days</strong>
                    </div>

                    <div class="stockout-metric">
                        <span>Supplier Lead Time</span>
                        <strong>${item.supplier_lead_time} days</strong>
                    </div>

                </div>

                <div class="stockout-action">
                    <strong>Recommended Action</strong>
                    <span>${actionMessage}</span>
                </div>

            </div>
        `;
    }).join("");
}


function renderSalesChanges(items) {
    const container = document.getElementById("sales-list");

    if (!items || items.length === 0) {
        container.innerHTML = "<p>No significant sales changes.</p>";
        return;
    }

    container.innerHTML = items.map(item => {

        const change = Number(item.percentage_change);
        const sign = change > 0 ? "+" : "";

        const type =
            item.anomaly_type === "SALES_SPIKE"
                ? "Sales Spike"
                : "Sales Drop";

        return `
            <div class="data-item">

                <div>
                    <strong>${item.product_id}</strong>
                    <span>${type}</span>
                </div>

                <strong class="sales-change">
                    ${sign}${change.toFixed(1)}%
                </strong>

            </div>
        `;
    }).join("");
}


function renderPriorities(items) {
    const container = document.getElementById("priority-list");

    if (!items || items.length === 0) {
        container.innerHTML = "<p>No priority issues identified.</p>";
        return;
    }

    container.innerHTML = items.slice(0, 8).map(item => {

        return `
            <div class="priority-card">

                <div class="priority-header">

                    <div>
                        <strong>${item.product_id}</strong>
                        <span>${item.store_id}</span>
                    </div>

                    <span class="priority-level">
                        ${item.priority_level}
                    </span>

                </div>

                <div class="priority-type">
                    ${item.issue_type.replaceAll("_", " ")}
                </div>

                <p>${item.reason}</p>

            </div>
        `;

    }).join("");
}


function setupCopilot() {
    const button = document.getElementById("ask-button");
    const input = document.getElementById("question-input");

    if (!button || !input) {
        return;
    }

    button.addEventListener("click", askCopilot);

    input.addEventListener("keydown", event => {
        if (event.key === "Enter") {
            askCopilot();
        }
    });
}


async function askCopilot() {
    const input = document.getElementById("question-input");
    const button = document.getElementById("ask-button");
    const responseBox = document.getElementById("copilot-response");
    const answerBox = document.getElementById("answer");

    const question = input.value.trim();

    if (!question) {
        answerBox.textContent = "Please enter a question.";
        responseBox.classList.remove("hidden");
        return;
    }

    button.disabled = true;
    button.textContent = "Thinking...";

    answerBox.textContent = "Analyzing verified retail data...";
    responseBox.classList.remove("hidden");

    try {
        const response = await fetch("/api/copilot", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Copilot request failed."
            );
        }

        answerBox.textContent =
            data.answer ||
            data.response ||
            "No response was returned.";

    } catch (error) {
        console.error("Copilot error:", error);

        answerBox.textContent =
            "Unable to process the question right now.";

    } finally {
        button.disabled = false;
        button.textContent = "Ask AI";
    }
}


function showDashboardError(message) {
    document.getElementById("stockout-list").innerHTML =
        `<p>${message}</p>`;

    document.getElementById("sales-list").innerHTML =
        `<p>${message}</p>`;

    document.getElementById("priority-list").innerHTML =
        `<p>${message}</p>`;
}