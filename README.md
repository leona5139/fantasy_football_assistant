The purpose of this project is to serve as an assistant for fantasy football in both the initial drafting (through recommendations) and subsequent week to week management (through an informational dashboard).

The project itself is split into two parts, one each for drafting and team management.

## Drafting
The draft assistant is not meant to serve as a fully autonomous draft agent, but instead is meant to serve as an additional source of information when drafting. 

Within the draft folder, there are two scripts: 
- The first is greedy.py which calculates a simple efficiency score for each player (which considers features such as projected points, positional needs, and round number). It then returns the player with the highest score.
- The second is mcts.py which uses a simple monte carlo search tree to attempt to capture the consequences of a given selection.

Both scripts perform reasonably well during simple testing of online mock drafts, but my recommendation for highest success would be to use both in tandem to get as much information as possible when drafting and make decisions based on your own discretion.

## Managing
The team management assistant takes the form of a dashboard that displays both your players and available waiver players with tags corresponding to various positive and negative attributes (such as being favored in upcoming games or trending downwards in recent fantasy points). 

The purpose of this tool is to quickly gather information that is not easily available natively in the fantasy football application. This application does not make any recommendations itself of who to add/drop or sit/play.