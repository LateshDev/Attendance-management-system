/**
 * Attendance Marking UI Logic
 * Fast, responsive, mobile-first touch handlers
 */

document.addEventListener('DOMContentLoaded', () => {
    const markAllPresentBtn = document.getElementById('btnMarkAllPresent');
    const markAllAbsentBtn = document.getElementById('btnMarkAllAbsent');
    const resetAllBtn = document.getElementById('btnResetAll');
    const attendanceForm = document.getElementById('attendanceForm');
    const saveTriggerBtn = document.getElementById('btnTriggerSave');
    const confirmSaveBtn = document.getElementById('btnConfirmSave');

    // Summary modal elements
    const summaryTotal = document.getElementById('summaryTotal');
    const summaryPresent = document.getElementById('summaryPresent');
    const summaryAbsent = document.getElementById('summaryAbsent');
    const summaryLeave = document.getElementById('summaryLeave');
    const summaryUnmarked = document.getElementById('summaryUnmarked');
    const unmarkedWarning = document.getElementById('unmarkedWarning');
    const unmarkedNamesList = document.getElementById('unmarkedNamesList');

    // Live counter badges
    const countTotal = document.getElementById('liveCountTotal');
    const countPresent = document.getElementById('liveCountPresent');
    const countAbsent = document.getElementById('liveCountAbsent');
    const countLeave = document.getElementById('liveCountLeave');
    const countUnmarked = document.getElementById('liveCountUnmarked');

    const studentRows = document.querySelectorAll('.student-attendance-row');

    // Update Counters
    function updateCounters() {
        let present = 0;
        let absent = 0;
        let leave = 0;
        let unmarked = 0;
        const total = studentRows.length;

        studentRows.forEach(row => {
            const studentId = row.dataset.studentId;
            const input = document.getElementById(`status_input_${studentId}`);
            const val = input ? input.value : '';

            if (val === 'Present') present++;
            else if (val === 'Absent') absent++;
            else if (val === 'Leave') leave++;
            else unmarked++;
        });

        if (countTotal) countTotal.textContent = total;
        if (countPresent) countPresent.textContent = present;
        if (countAbsent) countAbsent.textContent = absent;
        if (countLeave) countLeave.textContent = leave;
        if (countUnmarked) countUnmarked.textContent = unmarked;

        return { total, present, absent, leave, unmarked };
    }

    // Set Status for a Student
    function setStudentStatus(studentId, status) {
        const input = document.getElementById(`status_input_${studentId}`);
        if (input) input.value = status;

        const row = document.querySelector(`.student-attendance-row[data-student-id="${studentId}"]`);
        if (!row) return;

        const buttons = row.querySelectorAll('.status-btn');
        buttons.forEach(btn => {
            if (btn.dataset.status === status) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    // Bind individual button clicks
    studentRows.forEach(row => {
        const studentId = row.dataset.studentId;
        const buttons = row.querySelectorAll('.status-btn');

        buttons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const chosenStatus = btn.dataset.status;
                setStudentStatus(studentId, chosenStatus);
                updateCounters();
            });
        });
    });

    // Mark All Present
    if (markAllPresentBtn) {
        markAllPresentBtn.addEventListener('click', (e) => {
            e.preventDefault();
            studentRows.forEach(row => {
                // Do not overwrite approved leave unless user clicks individual student
                const isLeave = row.dataset.approvedLeave === 'true';
                if (!isLeave) {
                    setStudentStatus(row.dataset.studentId, 'Present');
                }
            });
            updateCounters();
        });
    }

    // Mark All Absent
    if (markAllAbsentBtn) {
        markAllAbsentBtn.addEventListener('click', (e) => {
            e.preventDefault();
            studentRows.forEach(row => {
                const isLeave = row.dataset.approvedLeave === 'true';
                if (!isLeave) {
                    setStudentStatus(row.dataset.studentId, 'Absent');
                }
            });
            updateCounters();
        });
    }

    // Reset All
    if (resetAllBtn) {
        resetAllBtn.addEventListener('click', (e) => {
            e.preventDefault();
            studentRows.forEach(row => {
                const isLeave = row.dataset.approvedLeave === 'true';
                if (isLeave) {
                    setStudentStatus(row.dataset.studentId, 'Leave');
                } else {
                    const input = document.getElementById(`status_input_${row.dataset.studentId}`);
                    if (input) input.value = '';
                    row.querySelectorAll('.status-btn').forEach(btn => btn.classList.remove('active'));
                }
            });
            updateCounters();
        });
    }

    // Review & Save Trigger: Show confirmation modal with summary
    if (saveTriggerBtn) {
        saveTriggerBtn.addEventListener('click', () => {
            const stats = updateCounters();

            if (summaryTotal) summaryTotal.textContent = stats.total;
            if (summaryPresent) summaryPresent.textContent = stats.present;
            if (summaryAbsent) summaryAbsent.textContent = stats.absent;
            if (summaryLeave) summaryLeave.textContent = stats.leave;
            if (summaryUnmarked) summaryUnmarked.textContent = stats.unmarked;

            const unmarkedNames = [];
            studentRows.forEach(row => {
                const input = document.getElementById(`status_input_${row.dataset.studentId}`);
                if (!input || !input.value) {
                    const name = row.querySelector('.student-name-text')?.textContent.trim() || 'Unknown';
                    unmarkedNames.push(name);
                }
            });

            if (unmarkedNames.length > 0) {
                if (unmarkedWarning) unmarkedWarning.classList.remove('d-none');
                if (unmarkedNamesList) unmarkedNamesList.textContent = unmarkedNames.join(', ');
            } else {
                if (unmarkedWarning) unmarkedWarning.classList.add('d-none');
            }

            const modalEl = document.getElementById('saveConfirmModal');
            if (modalEl) {
                const modal = new bootstrap.Modal(modalEl);
                modal.show();
            }
        });
    }

    // Final Commit Save
    if (confirmSaveBtn && attendanceForm) {
        confirmSaveBtn.addEventListener('click', () => {
            confirmSaveBtn.disabled = true;
            confirmSaveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Saving...';
            attendanceForm.submit();
        });
    }

    // Initial counter evaluation
    updateCounters();
});
