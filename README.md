# LEGO-Tracker
This tool was created to assist in separating a large collection of jumbled LEGO bricks back into their original sets. It makes heavy use of [Rebrickable’s API](https://rebrickable.com/api/) to gather lists of parts for a given set, complete with each part’s ID, color, description, and photo. These parts lists should help the user keep track of their physical brick collection with ease.

## Load Set
A created set can be selected from a dropdown list and loaded with the green "Load Set" button to display its list of parts in a grid. Each cell in the grid contains a unique part’s image, ID, color, quantity needed, and quantity had. 

The only editable field in each cell is the “have” field, which accepts any integer from 0 to the amount in the “need” field. When “have” equals “need”, the entire cell will be highlighted green, making it easy to tell which parts are still needed and which are not.

## Create Set
The blue “Create Set” button prompts the user to enter a set ID. If a set with that ID exists in the Rebrickable database, the program then pulls a list of parts for the set and creates a new .txt file in the "Set Data" directory to store the set’s data and keep track of any changes made to it. The newly-created file will immediately be available to select from the dropdown list to load it.

## Search Parts
The yellow "Search Set" button provides the user with a search bar to input search terms. Upon entering a search, the program looks through every set and gathers every part that is still needed. It then searches for the entered terms in the ID, color, category, and name fields for each needed part. If every term is found somewhere in those four fields, the part appears in the grid of results. Each part's cell in the results grid can be clicked on to reveal the sets and quantities it is needed in.

## Future Updates:

All of the core functions of the tool are considered complete. Future commits will likely focus on improving performance or fixing visual inconsistencies and aesthetics. 

However, a few smaller features may still be implemented, such as displaying collection statistics, changing settings within the program, and writing persistent notes for individual sets.