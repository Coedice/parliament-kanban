---
---

function openBill(billId) {
    // Remove any existing active tag
    active_tag = document.getElementsByClassName("active")[0];
    previous_active_bill = active_tag?.id;
    if (active_tag != null) {
        active_tag.classList.remove("active");
        history.replaceState(null, null, "#");
    }

    // Add active tag if it was not previously active
    if (billId != previous_active_bill) {
        document.getElementById(billId).classList.add("active");
        history.replaceState(null, null, "#" + billId);
    }
}

function ticketIsInCoalition(ticket) {
    coalitionParties = ["{{ site.data.parties | where: "group", "Coalition" | map: "name" | join: 'QQQ' | slugify | split: 'qqq' | join: '", "' }}"];
    for (const party of coalitionParties) {
        if (ticket.classList.contains(party)) {
            return true;
        }
    }
    return false;
}

function updateColumnCounts() {
    // Update column counts
    const columns = document.getElementsByClassName("column");
    for (const column of columns) {
        let total = 0;
        for (const ticket of column.getElementsByClassName("ticket")) {
            if (ticket.style.display != "none") {
                total++;
            }
        }
        column.getElementsByClassName("columnSize")[0].innerHTML = total;
    }
}

function filterByParty(party) {
    console.log(party);
    // Update active filter
    const previous_active_filter = document.getElementById("filters").getElementsByClassName("active-filter")[0];

    if (previous_active_filter != undefined) {
        previous_active_filter.classList.remove("active-filter");
    }

    if (previous_active_filter == undefined || !(party + "-filter" == previous_active_filter.id)) {
        document.getElementById(party + "-filter").classList.add("active-filter");
    }
    else {
        return filterByParty("clear-filter");
    }

    // Update tickets
    const tickets = document.getElementsByClassName("ticket");

    for (const ticket of tickets) {
        if (ticket.classList.contains(party) || party == "clear-filter" || party == "coalition" && ticketIsInCoalition(ticket)) {
            ticket.style.display = "block";
        } else {
            ticket.style.display = "none";
        }
    }

    updateColumnCounts();
}

function filterByDate(start, end) {
    const tickets = document.getElementsByClassName("ticket");

    if (end == null || end == "") {
        end = new Date();
    }

    if (start == null || start == "") {
        start = new Date(0);
    }

    for (const ticket of tickets) {
        if (ticket.dataset.date < start) {
            ticket.style.display = "none";
        } else if (ticket.dataset.date > end) {
            ticket.style.display = "none";
        } else {
            ticket.style.display = "block";
        }
    }

    updateColumnCounts();
}

function toggleStar(billId, editCookie = true) {
    const billElement = document.getElementById(billId);
    let cookieValue = "";

    if (editCookie) {
        if (document.cookie == "") {
            document.cookie = "starred=";
        }
        cookieValue = document.cookie.split("=")[1];
    }

    if (billElement.classList.contains("starred")) {
        billElement.classList.remove("starred");

        // Remove cookie from list of starred tickets
        if (editCookie) {
            document.cookie = "starred=" + cookieValue.split(",").filter((starredBillId) => starredBillId != billId).join(",");
        }
    } else {
        billElement.classList.add("starred");

        // Append cookie to list of starred tickets
        if (editCookie) {
            if (cookieValue == "") {
                document.cookie = "starred=" + billId;
            } else {
                document.cookie = document.cookie + "," + billId;
            }
        }
    }

    console.log("GGG cookies: " + document.cookie);
}

window.onload = () => {
    // Update starred tickets
    const starredBills = document.cookie.split("=")[1].split(",");
    for (const starredBill of starredBills) {
        toggleStar(starredBill, false);
    }

    // Update active ticket based on hash
    const hash = window.location.hash;

    if (hash) {
        const id = hash.substring(1); // Remove the '#' character
        openBill(id);
    }
};
