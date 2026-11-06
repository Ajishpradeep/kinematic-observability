# Measured results

Real-data means weight each of the three evaluation participants equally. Synthetic means weight each of three seeds equally. Units and denominators are not pooled across these experiments.

## synthetic

| Lengths | Observations | Cap | Method | Wrist mm | Depth mm | Bend error ° | Reprojection px | Constraint deviation mm |
|---|---|---:|---|---:|---:|---:|---:|---:|
| oracle | uniform | 150 | Initial prediction | 101.524 | 51.075 | 8.292 | 25.450 | 17.156 |
| oracle | uniform | 150 | Length projection | 102.528 | 51.810 | 8.292 | 25.506 | 0.000 |
| oracle | uniform | 150 | FK + 3D tether | 100.711 | 50.854 | 8.025 | 25.116 | 0.000 |
| oracle | uniform | 150 | Cartesian + pixels | 53.073 | 50.119 | 5.244 | 0.573 | 17.250 |
| oracle | uniform | 150 | FK + pixels | 43.509 | 40.761 | 4.456 | 1.001 | 0.000 |
| oracle | uniform | 150 | FK + soft cap + pixels | 43.468 | 40.719 | 4.437 | 1.003 | 0.000 |
| oracle | uniform | 150 | FK + hard cap + pixels | 43.526 | 40.784 | 4.423 | 1.093 | 0.000 |
| oracle | weighted | 150 | Initial prediction | 101.524 | 51.075 | 8.292 | 25.450 | 17.156 |
| oracle | weighted | 150 | Length projection | 102.528 | 51.810 | 8.292 | 25.506 | 0.000 |
| oracle | weighted | 150 | FK + 3D tether | 100.711 | 50.854 | 8.025 | 25.116 | 0.000 |
| oracle | weighted | 150 | Cartesian + pixels | 53.073 | 50.119 | 5.244 | 0.573 | 17.250 |
| oracle | weighted | 150 | FK + pixels | 43.509 | 40.761 | 4.456 | 1.001 | 0.000 |
| oracle | weighted | 150 | FK + soft cap + pixels | 43.468 | 40.719 | 4.437 | 1.003 | 0.000 |
| oracle | weighted | 150 | FK + hard cap + pixels | 43.526 | 40.784 | 4.423 | 1.093 | 0.000 |
| generic | weighted | 150 | Initial prediction | 101.524 | 51.075 | 8.292 | 25.450 | 30.580 |
| generic | weighted | 150 | Length projection | 110.226 | 56.051 | 8.292 | 27.009 | 0.000 |
| generic | weighted | 150 | FK + 3D tether | 102.144 | 51.630 | 8.554 | 25.878 | 0.000 |
| generic | weighted | 150 | Cartesian + pixels | 53.073 | 50.119 | 5.244 | 0.573 | 31.492 |
| generic | weighted | 150 | FK + pixels | 55.036 | 51.839 | 8.314 | 1.821 | 0.000 |
| generic | weighted | 150 | FK + soft cap + pixels | 55.005 | 51.811 | 8.294 | 1.828 | 0.000 |
| generic | weighted | 150 | FK + hard cap + pixels | 54.992 | 51.740 | 7.921 | 2.018 | 0.000 |
| oracle | proximal_missing | 150 | Initial prediction | 101.524 | 51.075 | 8.292 | 33.797 | 17.156 |
| oracle | proximal_missing | 150 | Length projection | 102.528 | 51.810 | 8.292 | 33.897 | 0.000 |
| oracle | proximal_missing | 150 | FK + 3D tether | 100.711 | 50.854 | 8.025 | 33.376 | 0.000 |
| oracle | proximal_missing | 150 | Cartesian + pixels | 53.073 | 50.119 | 9.593 | 0.756 | 25.395 |
| oracle | proximal_missing | 150 | FK + pixels | 50.251 | 47.289 | 7.960 | 1.024 | 0.000 |
| oracle | proximal_missing | 150 | FK + soft cap + pixels | 50.188 | 47.224 | 7.904 | 1.025 | 0.000 |
| oracle | proximal_missing | 150 | FK + hard cap + pixels | 49.872 | 46.904 | 7.450 | 1.060 | 0.000 |
| generic | proximal_missing | 150 | Initial prediction | 101.524 | 51.075 | 8.292 | 33.797 | 30.580 |
| generic | proximal_missing | 150 | Length projection | 110.226 | 56.051 | 8.292 | 36.513 | 0.000 |
| generic | proximal_missing | 150 | FK + 3D tether | 102.144 | 51.630 | 8.554 | 33.888 | 0.000 |
| generic | proximal_missing | 150 | Cartesian + pixels | 53.073 | 50.119 | 9.593 | 0.756 | 36.397 |
| generic | proximal_missing | 150 | FK + pixels | 51.486 | 48.665 | 8.308 | 1.055 | 0.000 |
| generic | proximal_missing | 150 | FK + soft cap + pixels | 51.419 | 48.597 | 8.253 | 1.056 | 0.000 |
| generic | proximal_missing | 150 | FK + hard cap + pixels | 51.095 | 48.242 | 7.716 | 1.095 | 0.000 |
| oracle | distal_wrong | 150 | Initial prediction | 101.524 | 51.075 | 8.292 | 43.923 | 17.156 |
| oracle | distal_wrong | 150 | Length projection | 102.528 | 51.810 | 8.292 | 43.808 | 0.000 |
| oracle | distal_wrong | 150 | FK + 3D tether | 100.711 | 50.854 | 8.025 | 43.562 | 0.000 |
| oracle | distal_wrong | 150 | Cartesian + pixels | 94.894 | 50.944 | 11.881 | 1.015 | 31.492 |
| oracle | distal_wrong | 150 | FK + pixels | 93.001 | 49.519 | 10.173 | 1.445 | 0.000 |
| oracle | distal_wrong | 150 | FK + soft cap + pixels | 92.966 | 49.502 | 10.090 | 1.447 | 0.000 |
| oracle | distal_wrong | 150 | FK + hard cap + pixels | 92.653 | 49.148 | 8.744 | 1.507 | 0.000 |
| oracle_minus10 | weighted | 150 | Initial prediction | 101.524 | 51.075 | 8.292 | 25.450 | 32.354 |
| oracle_minus10 | weighted | 150 | Length projection | 107.702 | 54.372 | 8.292 | 26.432 | 0.000 |
| oracle_minus10 | weighted | 150 | FK + 3D tether | 100.654 | 50.684 | 8.839 | 25.518 | 0.000 |
| oracle_minus10 | weighted | 150 | Cartesian + pixels | 53.073 | 50.119 | 5.244 | 0.573 | 31.470 |
| oracle_minus10 | weighted | 150 | FK + pixels | 53.960 | 50.371 | 7.610 | 2.649 | 0.000 |
| oracle_minus10 | weighted | 150 | FK + soft cap + pixels | 53.936 | 50.346 | 7.595 | 2.650 | 0.000 |
| oracle_minus10 | weighted | 150 | FK + hard cap + pixels | 53.949 | 50.331 | 7.445 | 2.724 | 0.000 |
| oracle_plus10 | weighted | 150 | Initial prediction | 101.524 | 51.075 | 8.292 | 25.450 | 28.980 |
| oracle_plus10 | weighted | 150 | Length projection | 114.907 | 58.842 | 8.292 | 27.687 | 0.000 |
| oracle_plus10 | weighted | 150 | FK + 3D tether | 103.684 | 52.488 | 8.991 | 26.103 | 0.000 |
| oracle_plus10 | weighted | 150 | Cartesian + pixels | 53.073 | 50.119 | 5.244 | 0.573 | 30.610 |
| oracle_plus10 | weighted | 150 | FK + pixels | 59.909 | 56.989 | 9.460 | 1.073 | 0.000 |
| oracle_plus10 | weighted | 150 | FK + soft cap + pixels | 59.783 | 56.862 | 9.412 | 1.087 | 0.000 |
| oracle_plus10 | weighted | 150 | FK + hard cap + pixels | 60.007 | 57.021 | 8.858 | 1.316 | 0.000 |
| oracle | weighted | 90 | Initial prediction | 101.524 | 51.075 | 8.292 | 25.450 | 17.156 |
| oracle | weighted | 90 | Length projection | 102.528 | 51.810 | 8.292 | 25.506 | 0.000 |
| oracle | weighted | 90 | FK + 3D tether | 100.711 | 50.854 | 8.025 | 25.116 | 0.000 |
| oracle | weighted | 90 | Cartesian + pixels | 53.073 | 50.119 | 5.244 | 0.573 | 17.250 |
| oracle | weighted | 90 | FK + pixels | 43.509 | 40.761 | 4.456 | 1.001 | 0.000 |
| oracle | weighted | 90 | FK + soft cap + pixels | 52.694 | 49.768 | 9.110 | 1.648 | 0.000 |
| oracle | weighted | 90 | FK + hard cap + pixels | 68.785 | 65.527 | 14.683 | 3.024 | 0.000 |

### Evaluation units

| Unit | Retained chains | Raw wrist mm | FK + pixels wrist mm | Hard 150° wrist mm |
|---|---:|---:|---:|---:|
| seed17 | 512 | 99.358 | 43.008 | 42.827 |
| seed29 | 512 | 100.791 | 42.871 | 42.968 |
| seed43 | 512 | 104.422 | 44.647 | 44.783 |
## optitrack

| Lengths | Observations | Cap | Method | Wrist mm | Depth mm | Bend error ° | Reprojection px | Constraint deviation mm |
|---|---|---:|---|---:|---:|---:|---:|---:|
| oracle | uniform | 150 | Initial prediction | 78.336 | 49.552 | 17.185 | 17.907 | 18.825 |
| oracle | uniform | 150 | Length projection | 83.180 | 47.135 | 17.185 | 19.101 | 0.000 |
| oracle | uniform | 150 | FK + 3D tether | 78.365 | 48.509 | 15.610 | 18.061 | 0.000 |
| oracle | uniform | 150 | Cartesian + pixels | 76.174 | 48.281 | 17.480 | 0.351 | 24.744 |
| oracle | uniform | 150 | FK + pixels | 80.398 | 53.227 | 19.090 | 1.330 | 0.000 |
| oracle | uniform | 150 | FK + soft cap + pixels | 80.398 | 53.226 | 19.089 | 1.330 | 0.000 |
| oracle | uniform | 150 | FK + hard cap + pixels | 80.078 | 52.846 | 18.801 | 1.359 | 0.000 |
| oracle | weighted | 150 | Initial prediction | 78.336 | 49.552 | 17.185 | 17.907 | 18.825 |
| oracle | weighted | 150 | Length projection | 83.180 | 47.135 | 17.185 | 19.101 | 0.000 |
| oracle | weighted | 150 | FK + 3D tether | 78.365 | 48.509 | 15.610 | 18.061 | 0.000 |
| oracle | weighted | 150 | Cartesian + pixels | 76.163 | 48.281 | 17.477 | 0.370 | 24.731 |
| oracle | weighted | 150 | FK + pixels | 80.304 | 53.123 | 19.069 | 1.360 | 0.000 |
| oracle | weighted | 150 | FK + soft cap + pixels | 80.304 | 53.123 | 19.068 | 1.360 | 0.000 |
| oracle | weighted | 150 | FK + hard cap + pixels | 80.025 | 52.788 | 18.788 | 1.388 | 0.000 |
| generic | weighted | 150 | Initial prediction | 78.336 | 49.552 | 17.185 | 17.907 | 11.010 |
| generic | weighted | 150 | Length projection | 80.069 | 49.040 | 17.185 | 19.051 | 0.000 |
| generic | weighted | 150 | FK + 3D tether | 79.538 | 49.832 | 18.065 | 18.365 | 0.000 |
| generic | weighted | 150 | Cartesian + pixels | 76.163 | 48.281 | 17.477 | 0.370 | 25.377 |
| generic | weighted | 150 | FK + pixels | 83.471 | 57.303 | 20.784 | 0.805 | 0.000 |
| generic | weighted | 150 | FK + soft cap + pixels | 83.471 | 57.303 | 20.783 | 0.805 | 0.000 |
| generic | weighted | 150 | FK + hard cap + pixels | 83.775 | 57.577 | 20.432 | 0.839 | 0.000 |
| oracle | proximal_missing | 150 | Initial prediction | 78.336 | 49.552 | 17.185 | 19.583 | 18.825 |
| oracle | proximal_missing | 150 | Length projection | 83.180 | 47.135 | 17.185 | 22.733 | 0.000 |
| oracle | proximal_missing | 150 | FK + 3D tether | 78.365 | 48.509 | 15.610 | 19.751 | 0.000 |
| oracle | proximal_missing | 150 | Cartesian + pixels | 76.163 | 48.281 | 17.730 | 0.395 | 26.481 |
| oracle | proximal_missing | 150 | FK + pixels | 76.209 | 48.156 | 17.472 | 0.608 | 0.000 |
| oracle | proximal_missing | 150 | FK + soft cap + pixels | 76.209 | 48.156 | 17.472 | 0.608 | 0.000 |
| oracle | proximal_missing | 150 | FK + hard cap + pixels | 75.944 | 47.731 | 17.292 | 0.629 | 0.000 |
| generic | proximal_missing | 150 | Initial prediction | 78.336 | 49.552 | 17.185 | 19.583 | 11.010 |
| generic | proximal_missing | 150 | Length projection | 80.069 | 49.040 | 17.185 | 21.974 | 0.000 |
| generic | proximal_missing | 150 | FK + 3D tether | 79.538 | 49.832 | 18.065 | 20.425 | 0.000 |
| generic | proximal_missing | 150 | Cartesian + pixels | 76.163 | 48.281 | 17.730 | 0.395 | 20.896 |
| generic | proximal_missing | 150 | FK + pixels | 77.996 | 50.555 | 19.647 | 0.609 | 0.000 |
| generic | proximal_missing | 150 | FK + soft cap + pixels | 77.996 | 50.555 | 19.647 | 0.609 | 0.000 |
| generic | proximal_missing | 150 | FK + hard cap + pixels | 77.692 | 50.096 | 19.011 | 0.635 | 0.000 |
| oracle | distal_wrong | 150 | Initial prediction | 78.336 | 49.552 | 17.185 | 40.023 | 18.825 |
| oracle | distal_wrong | 150 | Length projection | 83.180 | 47.135 | 17.185 | 38.477 | 0.000 |
| oracle | distal_wrong | 150 | FK + 3D tether | 78.365 | 48.509 | 15.610 | 39.509 | 0.000 |
| oracle | distal_wrong | 150 | Cartesian + pixels | 106.692 | 48.801 | 23.421 | 0.773 | 34.131 |
| oracle | distal_wrong | 150 | FK + pixels | 107.454 | 50.204 | 21.491 | 1.135 | 0.000 |
| oracle | distal_wrong | 150 | FK + soft cap + pixels | 107.454 | 50.203 | 21.491 | 1.135 | 0.000 |
| oracle | distal_wrong | 150 | FK + hard cap + pixels | 107.015 | 49.559 | 20.103 | 1.188 | 0.000 |
| oracle_minus10 | weighted | 150 | Initial prediction | 78.336 | 49.552 | 17.185 | 17.907 | 36.730 |
| oracle_minus10 | weighted | 150 | Length projection | 99.859 | 51.776 | 17.185 | 21.370 | 0.000 |
| oracle_minus10 | weighted | 150 | FK + 3D tether | 80.140 | 48.068 | 13.672 | 18.654 | 0.000 |
| oracle_minus10 | weighted | 150 | Cartesian + pixels | 76.163 | 48.281 | 17.477 | 0.370 | 33.846 |
| oracle_minus10 | weighted | 150 | FK + pixels | 86.400 | 59.152 | 18.924 | 2.926 | 0.000 |
| oracle_minus10 | weighted | 150 | FK + soft cap + pixels | 86.400 | 59.152 | 18.924 | 2.926 | 0.000 |
| oracle_minus10 | weighted | 150 | FK + hard cap + pixels | 86.139 | 58.799 | 18.558 | 2.946 | 0.000 |
| oracle_plus10 | weighted | 150 | Initial prediction | 78.336 | 49.552 | 17.185 | 17.907 | 20.482 |
| oracle_plus10 | weighted | 150 | Length projection | 82.450 | 49.281 | 17.185 | 20.326 | 0.000 |
| oracle_plus10 | weighted | 150 | FK + 3D tether | 80.122 | 49.844 | 19.032 | 19.073 | 0.000 |
| oracle_plus10 | weighted | 150 | Cartesian + pixels | 76.163 | 48.281 | 17.477 | 0.370 | 31.890 |
| oracle_plus10 | weighted | 150 | FK + pixels | 87.691 | 62.410 | 22.248 | 0.883 | 0.000 |
| oracle_plus10 | weighted | 150 | FK + soft cap + pixels | 87.691 | 62.410 | 22.247 | 0.883 | 0.000 |
| oracle_plus10 | weighted | 150 | FK + hard cap + pixels | 87.677 | 62.278 | 21.719 | 0.929 | 0.000 |
| oracle | weighted | 90 | Initial prediction | 78.336 | 49.552 | 17.185 | 17.907 | 18.825 |
| oracle | weighted | 90 | Length projection | 83.180 | 47.135 | 17.185 | 19.101 | 0.000 |
| oracle | weighted | 90 | FK + 3D tether | 78.365 | 48.509 | 15.610 | 18.061 | 0.000 |
| oracle | weighted | 90 | Cartesian + pixels | 76.163 | 48.281 | 17.477 | 0.370 | 24.731 |
| oracle | weighted | 90 | FK + pixels | 80.304 | 53.123 | 19.069 | 1.360 | 0.000 |
| oracle | weighted | 90 | FK + soft cap + pixels | 81.102 | 54.238 | 19.385 | 1.726 | 0.000 |
| oracle | weighted | 90 | FK + hard cap + pixels | 83.386 | 56.944 | 19.505 | 2.755 | 0.000 |

### Evaluation units

| Unit | Retained chains | Raw wrist mm | FK + pixels wrist mm | Hard 150° wrist mm |
|---|---:|---:|---:|---:|
| P01 | 2586 | 78.324 | 71.683 | 71.485 |
| P05 | 1480 | 77.830 | 92.457 | 92.455 |
| P07 | 1348 | 78.856 | 76.772 | 76.135 |
