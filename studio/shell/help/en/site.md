# An object of several controllers

One `projekt.epw` describes **one** controller. A real installation is
often bigger: a house with a controller in the boiler room and another
at the gate, a plant with several cabinets. An `obiekt.epwsite` file
ties them into one whole.

## What an object is

A list of controllers — a name and a path to each one's project file.
The projects stay separate files in their own folders; the object does
not absorb them.

## The File menu

| Item | What it does |
|---|---|
| **New Object** | an empty object, asks for a name |
| **Open Object** | loads an `obiekt.epwsite` and its controllers |
| **Add Controller to Object** | a new, empty project as another device |
| **Add Existing Project** | attaches a `projekt.epw` you already have |
| **Save Object** | saves **all** the controllers at once |

"Save" on the top toolbar saves only the **active** controller.

## Switching

Clicking a controller in the list switches the whole tree below to its
project. The editors hand over their documents on the switch — unsaved
edits are not lost, and the controller stays red with an asterisk until
you save it.

## Removing

**Remove Controller from Object** takes it off the list — **the project
file stays on disk**. If it has unsaved edits, Studio asks outright
whether to discard them. An object needs at least one controller.

## Why, beyond tidiness

So controllers can see each other's values. That is what [Object
Links](help://object_links) do — one controller's point becomes a
`Link.*` tag on another, over MQTT.
