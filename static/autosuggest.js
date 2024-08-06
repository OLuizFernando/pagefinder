let avaliableTitles = window.titles
let avaliableNames = window.names

const titlesSuggestions = document.getElementById("titlesSuggestions")
const titleInput = document.getElementById("titleInput")

const namesSuggestions = document.getElementById("namesSuggestions")
const nameInput = document.getElementById("nameInput")

titleInput.onkeyup = function() {
    let result = []
    let input = titleInput.value

    if (input.length) {
        titlesSuggestions.style.display = "block"
        result = avaliableTitles.filter((title) => {
            return title.toLowerCase().includes(input.toLowerCase())
        })
    }

    displayTitles(result)

    if (!result.length) {
        titlesSuggestions.innerHTML = ""
    }
}

nameInput.onkeyup = function() {
    let result = []
    let input = nameInput.value

    if (input.length) {
        namesSuggestions.style.display = "block"
        result = avaliableNames.filter((name) => {
            return name.toLowerCase().includes(input.toLowerCase())
        })
    }

    displayNames(result)

    if (!result.length) {
        namesSuggestions.innerHTML = ""
    }
}

function displayTitles(result) {
    const content = result.map((list) => {
        return "<li onclick=selectTitleInput(this)>" + list + "</li>"
    })

    titlesSuggestions.innerHTML = "<ul>" + content.join("") + "</ul>"
}

function displayNames(result) {
    const content = result.map((list) => {
        return "<li onclick=selectNameInput(this)>" + list + "</li>"
    })

    namesSuggestions.innerHTML = "<ul>" + content.join("") + "</ul>"
}

function selectTitleInput(list) {
    titleInput.value = list.innerHTML
    titlesSuggestions.innerHTML = ""
}

function selectNameInput(list) {
    nameInput.value = list.innerHTML
    namesSuggestions.innerHTML = ""
}