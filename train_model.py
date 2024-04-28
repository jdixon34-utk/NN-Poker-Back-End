import rlcard
from rlcard.agents import NFSPAgent
from rlcard.agents import RandomAgent
import torch
import os
import time
from rlcard.utils import (
  tournament,
  reorganize,
  Logger,
)

total_start_time = time.time()

ntrain = 600001 # total training games to play
ntest = 1000 # how many testing games to play for performance evaluation
testinterval = 5000 # how many training games to play between tests
checkpointinterval = 100000 # how many training games to play between creating checkpoints
updateinterval = 1000 # how many training games to play between printing training rate

# create environment
current_dir = os.getcwd()
env = rlcard.make('limit-holdem')
training_agent = NFSPAgent(num_actions=env.num_actions, state_shape=env.state_shape[0], hidden_layers_sizes=[1024, 512, 1024, 512], reservoir_buffer_capacity=30000000, batch_size=256, train_every=256, rl_learning_rate=0.0005, sl_learning_rate=0.0001, q_mlp_layers=[1024, 512, 1024, 512], q_replay_memory_size=600000, q_replay_memory_init_size=256, q_epsilon_start=0.08, q_epsilon_end=0, q_epsilon_decay_steps=int(1e6), q_batch_size=256, q_train_every=256, evaluate_with='best_response', device=torch.device('cuda:0'), save_path=current_dir, save_every=testinterval)
opposing_agent = NFSPAgent(num_actions=env.num_actions, state_shape=env.state_shape[0], hidden_layers_sizes=[1024, 512, 1024, 512], reservoir_buffer_capacity=30000000, batch_size=256, train_every=256, rl_learning_rate=0.0005, sl_learning_rate=0.0001, q_mlp_layers=[1024, 512, 1024, 512], q_replay_memory_size=600000, q_replay_memory_init_size=256, q_epsilon_start=0.08, q_epsilon_end=0, q_epsilon_decay_steps=int(1e6), q_batch_size=256, q_train_every=256, evaluate_with='best_response', device=torch.device('cuda:0'), save_path=current_dir, save_every=testinterval)

# hyperparameters to optimize
rl_learning_rate_list = [0.0005]
sl_learning_rate_list = [0.0001]
q_replay_memory_init_size_list = [256]
q_epsilon_start_list = [0.08]
q_epsilon_decay_steps_list = [int(1e6)]

# for resuming training from checkpoints
# checkpointt = torch.load('250kv5t.pt')
# checkpointo = torch.load('250kv5o.pt')
# training_agent = NFSPAgent.from_checkpoint(checkpointt)
# opposing_agent = NFSPAgent.from_checkpoint(checkpointo)

print(f'using {training_agent.device}')
env.set_agents([training_agent, opposing_agent])

# run experiments and log progress
training_start_time = time.time()
with Logger("results/") as logger:
    for episode in range(ntrain):

        # select policy (best_response, average_policy)
        training_agent.sample_episode_policy()
        opposing_agent.sample_episode_policy()
        
        # Generate data from the environment
        trajectories, payoffs = env.run(is_training=True)

        # Reorganaize the data to be state, action, reward, next_state, done
        trajectories = reorganize(trajectories, payoffs)

        # Feed transitions into agent memories, and train both agents
        for ts in trajectories[0]:
          training_agent.feed(ts)
          opposing_agent.feed(ts)

        # evaluate performance against random agent
        if episode % testinterval == 0:
          control_agent = RandomAgent(num_actions=env.num_actions)
          env.set_agents([training_agent, control_agent])
          logger.log_performance(episode, tournament(env, ntest)[0])
          env.set_agents([training_agent, opposing_agent])

        # print training rate
        if episode % updateinterval == 0:
          print(f'\ntrained {updateinterval} episodes in {time.time() - training_start_time:.3f} seconds')
          training_start_time = time.time()

        # occasionally create checkpoints
        if episode % checkpointinterval == 0:
          # check on training_agent vs opposing_agent performance
          train_vs_opp = tournament(env, ntest)[0]
          print(f'\ntraining vs opposing: {train_vs_opp:.3f}')
          
          # make checkpoints
          if episode != 0:
            update_start_time = time.time()
            tfname = 'temp/v5tcp' + str(episode) + '.pt'
            ofname = 'temp/v5ocp' + str(episode) + '.pt'
            training_agent.save_checkpoint(path=current_dir, filename=tfname)
            opposing_agent.save_checkpoint(path=current_dir, filename=ofname)
            print(f'checkpoints created in {time.time() - update_start_time:.3f} seconds')


    # Get the paths
    csv_path, fig_path = logger.csv_path, logger.fig_path 

    print('\ncsv_path:', csv_path, '\nfig_path:', fig_path)
    training_agent.save_checkpoint(path=current_dir, filename='trained_t_rename_me_v7.pt')
    opposing_agent.save_checkpoint(path=current_dir, filename='trained_o_rename_me_v7.pt')

print(f'finished in {time.time() - total_start_time:.3f} seconds')