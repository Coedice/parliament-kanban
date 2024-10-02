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

window.onload = () => {
    const hash = window.location.hash;

    if (hash) {
        const id = hash.substring(1); // Remove the '#' character
        openBill(id);
    }
};
