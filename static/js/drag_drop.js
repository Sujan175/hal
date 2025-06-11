document.addEventListener('DOMContentLoaded', () => {
    const draggableItems = document.querySelectorAll('.draggable-item');
    const dropTargets = document.querySelectorAll('.drop-target'); // Includes the source container if classed as such
    const dadForm = document.getElementById('dad-form');
    const dadAnswersInput = document.getElementById('dad_answers_input');
    const draggableContainer = document.getElementById('draggable-container');

    let currentSelections = {}; // Stores { "draggedItemText": "dropTargetValue" }

    // Function to update the hidden input
    function updateHiddenInput() {
        dadAnswersInput.value = JSON.stringify(currentSelections);
        console.log("Updated hidden input:", dadAnswersInput.value);
    }

    // Initialize currentSelections from any pre-dropped items (e.g. if page reloads with state)
    // For this implementation, we start fresh each time. Could be enhanced later.

    draggableItems.forEach(item => {
        item.addEventListener('dragstart', (event) => {
            event.dataTransfer.setData('text/plain', event.target.id);
            event.dataTransfer.effectAllowed = 'move';
            event.target.classList.add('dragging');
            // console.log(`Drag Start: ${event.target.id}`);
        });

        item.addEventListener('dragend', (event) => {
            event.target.classList.remove('dragging');
            // console.log(`Drag End: ${event.target.id}`);
        });
    });

    dropTargets.forEach(target => {
        target.addEventListener('dragover', (event) => {
            event.preventDefault(); // Necessary to allow dropping
            target.classList.add('drag-over');
            // console.log(`Drag Over: ${target.dataset.targetValue || 'source_container'}`);
        });

        target.addEventListener('dragleave', (event) => {
            target.classList.remove('drag-over');
        });

        target.addEventListener('drop', (event) => {
            event.preventDefault();
            target.classList.remove('drag-over');

            const draggedItemId = event.dataTransfer.getData('text/plain');
            const draggedItem = document.getElementById(draggedItemId);

            if (!draggedItem) {
                console.error("Dragged item not found!");
                return;
            }

            const draggedItemText = draggedItem.dataset.itemValue || draggedItem.textContent.trim();
            const targetValue = target.dataset.targetValue; // Value of the drop target box

            // console.log(`Drop: Item ${draggedItemId} (${draggedItemText}) on Target ${targetValue}`);

            // Remove dragged item from its previous parent's selection entry if it was in one
            Object.keys(currentSelections).forEach(key => {
                if (key === draggedItemText) {
                    delete currentSelections[key];
                }
            });

            // If the target is a specific drop zone (not the source container)
            if (target !== draggableContainer) {
                // Check if the target already has an item.
                const existingItemInTarget = target.querySelector('.draggable-item');
                if (existingItemInTarget && existingItemInTarget !== draggedItem) {
                    // Move the existing item back to the draggable container
                    draggableContainer.appendChild(existingItemInTarget);
                    const existingItemText = existingItemInTarget.dataset.itemValue || existingItemInTarget.textContent.trim();
                    // console.log(`Returned ${existingItemText} to source container.`);
                    // Remove its old selection entry
                     delete currentSelections[existingItemText];
                }

                // Append the new dragged item to the target
                target.querySelector('.dropped-items-area').appendChild(draggedItem);
                currentSelections[draggedItemText] = targetValue;
                // console.log(`Dropped ${draggedItemText} onto ${targetValue}. Selections:`, currentSelections);
            } else { // Target is the draggableContainer (returning an item)
                draggableContainer.appendChild(draggedItem); // Append directly to draggable container
                // Item already removed from selections above
                // console.log(`Returned ${draggedItemText} to source container. Selections:`, currentSelections);
            }
            updateHiddenInput();
        });
    });

    if (dadForm) {
        dadForm.addEventListener('submit', (event) => {
            // The hidden input is already updated on each drop.
            // So, no specific action needed here other than ensuring it's populated.
            if (Object.keys(currentSelections).length === 0 && dadAnswersInput.value === "") {
                 // If nothing selected, and input is empty, ensure it's an empty JSON object
                dadAnswersInput.value = JSON.stringify({});
            }
            console.log('DAD form submitted with answers:', dadAnswersInput.value);
            // Allow default submission
        });
    }

    // Initial update in case of no interactions
    updateHiddenInput();
});
