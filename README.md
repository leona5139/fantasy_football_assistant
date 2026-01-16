# Fantasy Football Assistant
This season, I decided to participate in a fantasy football league, but unfortunately I don't really know anything about football. So instead, I decided to leverage my statistics and programming skills to assist me. This project covers both drafting and week-to-week management, and it led me to getting first in my league with an 87.5% winrate.

# Technologies/Techniques
- `Python`
- `Monte Carlo Tree Search`
- `Streamlit`

# The Process
Over the course of this project, I redid the draft optimization part many many times:
- My first strategy was regression to make estimates for the points of each player, but this was an unsuccessful apporach as even if I was able to make a model that perfectly predicted score, it still wouldn't help me with draft strategies
- My next strategy was using a transformer and historical draft data to learn relationships and drafting patterns; however, I was unable to find a good data set of previous drafts. I attempted to solve this problem by simulating drafts, but this would mean that my transformer would be an approximation of an approximation as it wasn't trained on real data.
- My third strategy was to use reinforcement learning, but unfortunately the drafting problem was too complicated and had too sparse of rewards to be able to effectively learn
- My final and most successful strategy was to use a combined approach of a greedy algorithm and Monte Carlo Tree Search (what is implemented in this repository). The greedy algorithm gave a less informed but quick suggestion while the MCTS gave a more detailed but more time consuming analysis. This would give me two points of reference for possible suggestions of player picks that I could then use to inform my final decision

After completing the draft tool, I then moved to the week-to-week management. Very quickly I realized that it was quite difficult to accurately predict player performance (especially better than what organizations like ESPN already provide) for weekly start/bench decisions, so instead I shifted my approach to helping with overall team robustness. The final dashboard is designed to highlight the overall trends of player performance and the difficulty of their upcoming matchups to help make roster change decisions to increase the depth of the roster.

# What I learned
## The first solution is not always the best solution
Throughout this process, I tried several different approaches, but they didn't always work. And although it was quite frustrating to have to restart multiple times, I am ultimately glad that I did because my final product was much better than what I could have attained if I just forced my one of my initial approaches.

## Breaking down ideas makes them much easier to learn
Several of the methodologies that I tried during this project were completely new to me, so trying to learn them and immediately apply them to such a complex problem was bound to be a disaster. So, instead, I tried learning each topic by starting with smaller toy examples before building up to the full project. This approach helped to ensure that I understood the methodologies that I was using and made the implementation and debugging process much easier.

## Overall Learnings
I think that the greatest learning from this project was the importance of resilience. There were multiple times throughout this project where I felt stuck with a broken methodology or intimidated by learning something new, and there were even times where I gave up and took a short break. Ultimately though, I saw the project through, and I am really glad that I did. I am very proud of my performance, and I definitely learned a lot.

# Future Improvements
- Improve the computational speed of the Monte Carlo Tree Search to allow me to have deeper searches for best players
- Refine the user interfaces to allow for greater accesibility (the end goal is for this project to be useable for someone without any technical know how)
- Add a feature to evaluate proposed trades and/or help find trades to propose

*Thanks for checking out my project! Feel free to explore the code and reach out if you have questions or ideas.*.
