"""Tolman experimental battery.

Cognitive-map probes from Tolman's 1940s rat-maze work, adapted to the
MPC Brain stack. Each experiment is a separate module.

  latent_learning   — explore without reward, then add goal; compare
                      time-to-goal vs a control trained with goal from
                      step zero. Tolman 1948.

  detour            — TODO. Pre-train on one path; block it; measure
                      adaptation.

  shortcut          — TODO. Pre-train on indirect path; open shortcut;
                      measure whether agent takes it.

  reversal          — TODO. Train goal at A; move to B; measure
                      relearning rate.
"""
