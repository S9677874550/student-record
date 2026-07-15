// static/js/app.js

// ------------------- Register page validation -------------------
const registerForm = document.getElementById("registerForm");
if (registerForm) {
    registerForm.addEventListener("submit", function (e) {
        const username = document.getElementById("username").value.trim();
        const phone = document.getElementById("phone").value.trim();
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const confirmPassword = document.getElementById("confirm_password").value;

        if (!/^[A-Za-z0-9_]{3,20}$/.test(username)) {
            alert("Username must be 3-20 characters (letters, numbers, underscore only)");
            e.preventDefault();
            return;
        }
        if (!/^[0-9]{10}$/.test(phone)) {
            alert("Phone Number must contain exactly 10 digits");
            e.preventDefault();
            return;
        }
        if (!/^[a-zA-Z0-9._%+-]+@gmail\.com$/.test(email)) {
            alert("Enter a valid @gmail.com address");
            e.preventDefault();
            return;
        }
        if (password.length < 6) {
            alert("Password must be at least 6 characters");
            e.preventDefault();
            return;
        }
        if (password !== confirmPassword) {
            alert("Password and Confirm Password do not match");
            e.preventDefault();
            return;
        }
        // all good -> form submits normally to /register
    });
}

// ------------------- Student registry page -------------------
const studentForm = document.getElementById("studentForm");
const formTitle = document.getElementById("formTitle");
const formSubmitBtn = document.getElementById("formSubmitBtn");
const cancelEditBtn = document.getElementById("cancelEditBtn");
const editIdField = document.getElementById("editId");

if (studentForm) {
    loadStudents();

    studentForm.addEventListener("submit", function (e) {
        e.preventDefault();

        const roll = document.getElementById("roll").value.trim();
        const name = document.getElementById("name").value.trim();
        const dept = document.getElementById("dept").value.trim();
        const email = document.getElementById("email").value.trim();
        const phone = document.getElementById("phone").value.trim();
        const editId = editIdField.value;

        if (!/^[0-9]+$/.test(roll)) {
            alert("Roll Number should contain only numbers");
            return;
        }
        if (!/^[A-Za-z ]+$/.test(name)) {
            alert("Name should contain only letters");
            return;
        }
        if (!/^[A-Za-z& ]+$/.test(dept)) {
            alert("Department should contain only letters (and '&' if needed)");
            return;
        }
        if (!/^[a-zA-Z0-9._%+-]+@gmail\.com$/.test(email)) {
            alert("Enter a valid @gmail.com address");
            return;
        }
        if (!/^[0-9]{10}$/.test(phone)) {
            alert("Phone Number must contain exactly 10 digits");
            return;
        }

        const payload = {
            roll_number: roll,
            name: name,
            department: dept,
            email: email,
            phone: phone
        };

        const isEdit = !!editId;
        const url = isEdit ? `/api/students/${editId}` : "/api/students";
        const method = isEdit ? "PUT" : "POST";

        fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
            .then((res) => res.json().then((data) => ({ status: res.status, data })))
            .then(({ status, data }) => {
                if (status >= 400) {
                    alert(data.error || "Something went wrong");
                    return;
                }
                exitEditMode();
                loadStudents();
            })
            .catch(() => alert("Server error. Please try again."));
    });

    cancelEditBtn.addEventListener("click", exitEditMode);
}

function exitEditMode() {
    studentForm.reset();
    editIdField.value = "";
    formTitle.textContent = "Add Student";
    formSubmitBtn.textContent = "Add Student";
    cancelEditBtn.style.display = "none";
}

function loadStudents() {
    fetch("/api/students")
        .then((res) => res.json())
        .then((students) => {
            const tbody = document.querySelector("#studentsTable tbody");
            tbody.innerHTML = "";
            students.forEach((s) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td data-label="Roll No">${s.roll_number}</td>
                    <td data-label="Name">${s.name}</td>
                    <td data-label="Department">${s.department}</td>
                    <td data-label="Email">${s.email}</td>
                    <td data-label="Phone">${s.phone}</td>
                    <td data-label="Action">
                        <button class="btn btn-edit" onclick="editStudent(${s.id})">Edit</button>
                        <button class="btn btn-delete" onclick="deleteStudent(${s.id})">Delete</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        });
}

function editStudent(id) {
    fetch(`/api/students/${id}`)
        .then((res) => res.json())
        .then((s) => {
            document.getElementById("editId").value = s.id;
            document.getElementById("roll").value = s.roll_number;
            document.getElementById("name").value = s.name;
            document.getElementById("dept").value = s.department;
            document.getElementById("email").value = s.email;
            document.getElementById("phone").value = s.phone;

            formTitle.textContent = "Edit Student";
            formSubmitBtn.textContent = "Update Student";
            cancelEditBtn.style.display = "inline-block";

            studentForm.scrollIntoView({ behavior: "smooth" });
        });
}

function deleteStudent(id) {
    if (!confirm("Delete this student?")) return;
    fetch(`/api/students/${id}`, { method: "DELETE" })
        .then((res) => res.json())
        .then(() => {
            // if the deleted student was mid-edit, reset the form
            if (editIdField.value == id) exitEditMode();
            loadStudents();
        });
}
