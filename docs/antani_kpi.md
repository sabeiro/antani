---
title: "Routific"
author: Giovanni Marelli
date: 2019-07-02
rights:  Creative Commons Non-Commercial Share Alike 3.0
language: en-US
output: 
	md_document:
		variant: markdown_strict+backtick_code_blocks+autolink_bare_uris+markdown_github
---

# optimization engine comparison

An optimization engine find the best combination for assigning tasks to a fleet.
To compare performances we create a set up of around 600 spots, 6 task types (with different priorities) and a fleet of 8 drivers

![setup](f_ops/comp_setup.png "comp setup")
_set up for the comparison_

We prepare the job file and we send it to the routific api service and [visualize the solution](http://routific-viewer.herokuapp.com/jobs/k24ozyff68)

![routific](f_ops/routific.png "routific")

_routific solution explorer_

We perform a visual inspection of routific work, we see that routes mix a lot

![routific_evaluation](f_ops/prob_1.png "routific evaluation")

_routes have internal intersection and operation areas cross_

Sequences don't make much sense

![routific mix](f_ops/routific_sequence.png "routific mix")

_routifix sequence_

In the city center where is harder to park many drivers cross the same streets

![routific mix](f_ops/routific_mix.png "routific mix")

_routifix mixing drivers_

There are some long deviations and once on the spot routific is ignoring neighboring tasks and skipping important priorities

![routific_evaluation](f_ops/prob_way.png "routific evaluation")

_long routes_

We observe long deviations for a single task

![routific_evaluation](f_ops/prob_single.png "routific evaluation")

_visual inspection of routific_

Even if we have [priority 1 over all tasks](http://routific-viewer.herokuapp.com/jobs/k2g4jwwj197) routes don't make much sense

![routific_evaluation prio1](f_ops/prob_prio1.png "routific evaluation")

_visual inspection of routific_

Long deviations for driving on a tunnel where the scooter is on the ground

![routific_tunnel](f_ops/prob_tunnel.png "routific evaluation")

_routed into a tunnel_

Routific returns more stops than the number of tasks

![routific_capacity](f_ops/routific_cheating.png "routific maximum capacity")

_routific and maximum capacity_


Routific returns only the total drive time and we have to reroute the segments to calculate the actula driven distance

# optimization engine

We can run the optimization engine from a blank system or after a routific solution.

![route engine](f_ops/route_engine.png "route engine")

_comparison between routing engine_

Starting from a routific solution we see that the optimization engine at first improves big springs

![routific_evaluation](f_ops/prob_2.png "routific evaluation")

_optimization improves big springs_

We use the following kpi:

* `completion`: percentage of van capacity filled
* `duration`: time spent
* `potential`: value of the van
* `distance`: distance of the route

The score is calculated via:

$$ score = \frac{occupancy * potential}{duration * distance} $$


![kpi comparison](f_ops/kpi_comparison.png "kpi comparison")

_comparison of kpi between engines_

<!-- If we consider routed distances the figure change -->

<!-- ![kpi comparison routed](f_ops/kpi_compRouted.png "kpi comparison routed") -->

<!-- _comparison of kpi between engines using routed distances_ -->


# single task move

The engine was at first focusing on single task move which was making convergency pretty slow. We started than introducing new moves and initial set up

![single spot move](f_ops/vid_blank.gif "single spot move")

_single spot move, solutions are a bit crowded_

each driver start from a different k-mean cluster

![start_clustering](f_ops/start_cluster.png "start clustering")

_distribution of the closest spot to a cluster_

We have than a better separation of routes

![single spot move](f_ops/vid_newMarkov.gif "single markov")

_single markov chain_

![single move energy](f_ops/nrg_blank.png "single move energy")

_energy evolution for single move engine_



## extrude, phantom, canonical

For speeding up operations we introduce a series of moves to improve run time and convergency.

*Extruding* is suggesting a chain following the Markov Chain probability

![extrude move](f_ops/vid_extrude.gif "extrude move")

_extrude move_

With extrusion we dicrease calculation time to 1/10 getting to the same run time as routific.

We realize that sometimes some routes get trapped in a local minimum and we can't get complete the occupancy of the van. Therefore we introduce *phantom* drivers so we have the option to discard uncomplete runs

![phantom move](f_ops/vid_phantom.gif "phantom move")

_phantom move_

Depending on the stage of the solution certain solutions are more appropriate than others

![nrg_canonical](f_ops/nrg_grand.png "energy canonical")

_energy distribution for canonical simulations_


To further improve convergence of solution we move to *gran canonical* simulation where we continously introduce and remove routes until we get to the best complete solution

![canonical move](f_ops/vid_canonical_trap.gif "canonical move")

_canonical move_

# run time

Routific was sending a complete solution within 3 minutes, the optimization engine was sending a better solution in 30 minutes, to speed up the process we introduced new moves

![execution time](f_ops/execution_time.png "execution time")

_execution time_

