function openBill(billId) {
    // Remove any existing active tag
    active_tag = document.getElementsByClassName("active")[0];
    previous_active_bill = active_tag?.id;
    if (active_tag != null) {
        active_tag.classList.remove("active");
        history.replaceState(null, null, "/");
    }

    // Add active tag if it was not previously active
    if (billId != previous_active_bill) {
        document.getElementById(billId).classList.add("active");
        history.replaceState(null, null, "#" + billId);
    }
}

window.onload = () => {
    const hash = window.location.hash;

    if (hash) {
        const id = hash.substring(1); // Remove the '#' character
        openBill(id);
    }
};
