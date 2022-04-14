from abc import ABC, abstractmethod
import numpy as np


class DynamicalSystem(ABC):
    """Abstract base class for a dynamical system

    Models a d-dimensional system of the following form:

      dq_j/dt = +dH/dp_j(q,p)
      dp_j/dt = -dH/dq_j(q,p)

    where j = 0,1,2,...,d-1
    """

    def __init__(self, dim, mass):
        """Construct new instance, set dimension and mass

        :arg dim: Spatial dimension of dynamical system
        :arg mass: Mass of the system (can be a scalar in 1d or a list in heigher dimensions)
        """
        self.dim = dim
        self.mass = mass
        self.dH_header_code = None
        self.dH_preamble_code = None
        self.dH_update_code = None
        self.separable = False

    @abstractmethod
    def compute_dHq(self, q, p, dHq):
        """Compute the derivative of the Hamiltonian with respect to position

        :arg q: Particle positions q (d-dimensional array)
        :arg p: Particle momenta (d-dimensional array)
        :arg dHq: Resulting vector dH/dq (d-dimensional array)
        :arg dHp: Resulting vector dH/dp (d-dimensional array)
        """

    @abstractmethod
    def compute_dHp(self, q, p, dHp):
        """Compute the derivative of the Hamiltonian with respect to momentum

        :arg q: Particle positions q (d-dimensional array)
        :arg p: Particle momenta (d-dimensional array)
        :arg dHp: Resulting vector dH/dp (d-dimensional array)
        """

    @abstractmethod
    def set_random_state(self, q, p):
        """Set the position q and momentum p to random values. This will be used
        during the training stage to pick a suitable set of initial values

        :arg q: Positions (d-dimensional array)
        :arg p: Momenta (d-dimensional array)
        """

    @abstractmethod
    def energy(self, q, p):
        """Return the total energy for given positions and momenta

        :arg q: Positions (d-dimensional array)
        :arg p: Canonical momenta (d-dimensional array)
        """

    def forward_map(self, q0, p0, t):
        """Exact forward map

        Compute position q(t) and momenta v(t), given initial position q(0) and momentum p(0).
        This will only be implemented if the specific dynamical system has an analytical solution

        :arg q0: initial position q(0)
        :arg p0: initial momentum p(0)
        :arg t: final time
        """
        raise NotImplementedError("Dynamical system has no exact solution.")


class HarmonicOscillator(DynamicalSystem):
    """One-dimensional harmonic oscillator

    The system is described by the Hamiltonian

    H(q,p) = p^2/(2*m) + 1/2*k_{spring}*q^2

    which results in the following equations of motion:

    dq/dt = p/m, dp/dt = -k*q
    """

    def __init__(self, mass, k_spring):
        """Construct new instance of harmonic oscillator class

        :arg mass: Particle mass
        :arg k_spring: Spring constant k
        """
        super().__init__(1, mass)
        self.separable = True
        self.k_spring = k_spring
        # C-code snipped for computing the dH update
        self.dHq_update_code = f"dHq[0] = ({self.k_spring})*q[0];"
        self.dHp_update_code = f"dHp[0] = 1.0/({self.mass})*p[0];"

    def compute_dHq(self, q, p, dHq):
        """Compute dH/dq

        Returns dH/dq = k_{spring}*q

        :arg q: Particle position q (1-dimensional array)
        :arg p: Particle momentum p (1-dimensional array)
        :arg dHq: Resulting dH/dq
        """
        dHq[0] = self.k_spring * q[0]

    def compute_dHp(self, q, p, dHp):
        """Compute dH/dp

        Returns dH/dp = p/mass

        :arg q: Particle position q (1-dimensional array)
        :arg p: Particle momentum q (1-dimensional array)
        :arg dHp: Resulting dH/dp
        """
        dHp[0] = p[0] / self.mass

    def set_random_state(self, q, p):
        """Draw position and momentum from a normal distribution
        :arg q: Position (1-dimensional array)
        :arg p: Momentum (1-dimensional array)
        """
        q[0] = np.random.normal(0, 1)
        p[0] = np.random.normal(0, 1)

    def energy(self, q, p):
        """Compute total energy E = p^2/(2*m) + 1/2*k*q^2

        :arg q: Position (1-dimensional array)
        :arg p: Momentum (1-dimensional array)
        """
        return 0.5 * p[0] ** 2 / self.mass + 0.5 * self.k_spring * q[0] ** 2

    def forward_map(self, q0, p0, t):
        """Exact forward map

        Compute position q(t) and momentum p(t), given initial position q(0) and momentum p(0).

        For this use:

        q(t) = q(0)*cos(omega*t) + p(0)/(m*omega)*sin(omega*t)
        p(t) = -m*q(0)*omega*sin(omega*t) + p(0)*cos(omega*t)

        with omega = sqrt(k/m), k = k_{spring}, m = mass

        :arg q0: initial position q(0)
        :arg p0: initial momentum p(0)
        :arg t: final time
        """
        omega = np.sqrt(self.k_spring / self.mass)
        cos_omegat = np.cos(omega * t)
        sin_omegat = np.sin(omega * t)
        q = np.array(q0[0] * cos_omegat + p0[0] / (omega * self.mass) * sin_omegat)
        p = np.array(-q0[0] * self.mass * omega * sin_omegat + p0[0] * cos_omegat)
        return q, p


class DoublePendulum(DynamicalSystem):
    """2-dimensional double pendulum

    The double pendulum is described by the following Lagrangian:

      L = 1/2*(m_0+m_1)*L_0^2 * (dtheta_0/dt)^2  + 1/2*m_1*L_1^2 * (dtheta_1/dt)^2
          + m_1*L_0*L_1*(dtheta_0/dt)*(dtheta_1/dt)*cos(theta_0-theta_1)
          - (m_0+m_1)*g*L_0*(1 - cos(theta_0)) - m_1*g*L_1*(1 - cos(theta_1))

    The resulting canonical momenta are

      p_0 = (m_0+m_1)*L_0^2*dtheta_0/dt + m_1*L_0*L_1*dtheta_1/dt*cos(theta_0-theta_1)
      p_1 = m_1*L_1^2*dtheta_1/dt + m_1*L_0*L_1*dtheta_0/dt*cos(theta_0-theta_1)

    This leads to the equations of motion:

      dtheta_0/dt = ( L_1*p_0 - L_0*p_1*cos(theta_0-theta_1) ) * kappa / L_0
      dtheta_1/dt = ( -L_1*p_0*cos(theta_0-theta_1) + (1+m_0/m_1)*L_0*p_1 ) * kappa / L_1
      dp_0/dt = -(m_0+m_1)*g*L_0*sin(theta_0) - h_0 + h_1*sin(2*(theta_0-theta_1))
      dp_1/dt = -m_1*g*L_1*sin(theta_1) + h_0 - h_1*sin(2*(theta_0-theta_1))

    with

      kappa = 1 / (L_0 * L_1 * (m_0 + m_1*sin^2(theta_0-theta_1)))
      h_0 = p_0*p_1*sin(theta_0-theta_1) * kappa
      h_1 = (m_1*L_1^2*p_0^2 + (m_0+m_1)*L_0^2*p_1^2
             - 2*m_1*L_0*L_1*p_0*p_1*cos(theta_0-theta_1)) * kappa^2 / 2
    """

    def __init__(self, mass, L0, L1, g_grav=9.81):
        """Construct new instance of double pendulum class.

        :arg mass: Particle mass (list of length two)
        :arg g_grav: gravitional acceleration constant
        :arg L0: length of first segment of double pendulum
        :arg L1: length of second segment of double pendulum
        """
        super().__init__(2, mass)
        self.g_grav = g_grav
        self.L0 = L0
        self.L1 = L1
        # C-code snipped for computing the acceleration update
        self.dH_header_code = """
        #include "math.h"
        """
        self.dH_preamble_code = """
        double cos_q0_q1;
        double sin_q0_q1;
        double sin_2_q0_q1;
        double sin_q0;
        double sin_q1;
        """
        self.dHq_update_code = f"""
        cos_q0_q1 = cos(q[0]-q[1]);
        sin_q0_q1 = sin(q[0]-q[1]);
        sin_2_q0_q1 = sin(2.*(q[0]-q[1]));
        sin_q0 = sin(q[0]);
        sin_q1 = sin(q[1]);
        kappa = 1 / ({self.L0} * {self.L1} * ({self.mass[0]} + {self.mass[1]})*sin_q0_q1*sin_q0_q1);
        h0 = p[0]*p[1]*sin_q0_q1 * kappa;
        h1 = 0.5 * ({self.mass[1]}*{self.L1}*{self.L1}*p[0]*p[0] 
             + ({self.mass[0]}+{self.mass[1]}) * {self.L0}*{self.L0}*p[1]*p[1]
             - 2*{self.mass[1]}*{self.L0}*{self.L1}*p[0]*p[1]*cos_q0_q1) * kappa * kappa;
        dHq[0] = ({self.mass[0]}+{self.mass[0]})*{self.g_grav}*{self.L0}*sin_q0
                  + h0 - h1 * sin_2_q0_q1;
        dHq[1] = {self.mass[1]}*{self.g_grav}*{self.L1}*sin_q1 
                  - h0 + h1 * sin_2_q0_q1;
        """
        self.dHp_update_code = f"""
        cos_q0_q1 = cos(q[0]-q[1]);
        sin_q0_q1 = sin(q[0]-q[1]);
        sin_2_q0_q1 = sin(2.*(q[0]-q[1]));
        sin_q0 = sin(q[0]);
        sin_q1 = sin(q[1]);
        kappa = 1 / ({self.L0} * {self.L1} * ({self.mass[0]} + {self.mass[1]})*sin_q0_q1*sin_q0_q1);
        dHp[0] = ( {self.L1}*p[0] - {self.L0}*p[1]*cos_q0_q1 ) * kappa / {self.L0};
        dHp[1] = ( -{self.L1}*p[0]*cos_q0_q1 
                    + (1.+{self.mass[0]}/{self.mass[1]})*{self.L0}*p[1] ) * kappa / {self.L1};
        """

    def _kappa(self, q):
        """Compute kappa = 1 / (L_0 * L_1 * (m_0 + m_1*sin^2(theta_0-theta_1)))

        :arg q: Position angles (2-dimensional array)
        """
        return 1 / (
            self.L0 * self.L1 * (self.mass[0] + self.mass[1]) * np.sin(q[0] - q[1]) ** 2
        )

    def compute_dHq(self, q, p, dHq):
        """Compute dH/dq

        :arg q: angles of bobs wrt vertical (2-dimensional array)
        :arg p: corresponding canonical momenta (2-dimensional array)
        :arg dHq: resulting dH/dq
        """
        kappa = self._kappa(q)
        h0 = p[0] * p[1] * np.sin(q[0] - q[1]) * kappa
        h1 = (
            (
                self.mass[1] * self.L1**2 * p[0] * p[0]
                + (self.mass[0] + self.mass[1]) * self.L0**2 * p[1] ** 2
                - 2
                * self.mass[1]
                * self.L0
                * self.L1
                * p[0]
                * p[1]
                * np.cos(q[0] - q[1])
            )
            * kappa**2
            / 2
        )

        dHq[0] = (
            (self.mass[0] + self.mass[0]) * self.g_grav * self.L0 * np.sin(q[0])
            + h0
            - h1 * np.sin(2 * (q[0] - q[1]))
        )
        dHq[1] = (
            self.mass[1] * self.g_grav * self.L1 * np.sin(q[1])
            - h0
            + h1 * np.sin(2 * (q[0] - q[1]))
        )

    def compute_dHp(self, q, p, dHp):
        """Compute dH/dp

        :arg q: angles of bobs wrt vertical (2-dimensional array)
        :arg p: corresponding canonical momenta (2-dimensional array)
        :arg dHq: resulting dH/dp
        """
        kappa = self._kappa(q)
        dHp[0] = (
            (self.L1 * p[0] - self.L0 * p[1] * np.cos(q[0] - q[1])) * kappa / self.L0
        )
        dHp[1] = (
            (
                -self.L1 * p[0] * np.cos(q[0] - q[1])
                + (1.0 + self.mass[0] / self.mass[1]) * self.L0 * p[1]
            )
            * kappa
            / self.L1
        )

    def set_random_state(self, q, p):
        """Draw position and angular velocity from a normal distribution

        :arg q: Angles with vertical (2-dimensional array)
        :arg p: Canonical momenta (2-dimensional array)
        """

        q[0:2] = np.random.normal(0, 0.5 * np.pi, size=(2))  # angles of two bobs
        p[0:2] = np.random.normal(0, 1, size=(2))  # canonical momenta of two bobs

    def energy(self, q, p):
        """Compute total energy

        The potential and kinetic energy is given by

          V_pot = (m_0 + m_1)*g*L_0*(1-cos(theta_0)) + m_1*g*L_1*(1-cos(theta_1))
          T_kin = ( L_1^2*p_0^2 + (1+m_0/m_1)*L_0^2*p_1^2 - 2*L_0*L_1*p_0*p_1*cos(theta_0-theta_1) )
                * kappa^2 / ( 2 * L_0*L_1)

          with kappa as defined above

        :arg q: Angles with vertical (2-dimensional array)
        :arg p: Corresponding canonical momenta (2-dimensional array)
        """

        # Potential Energy
        V_pot = self.g_grav * (
            (self.mass[0] + self.mass[1]) * self.L0 * (1 - np.cos(q[0]))
            + self.mass[1] * self.L1 * (1 - np.cos(q[1]))
        )
        T_kin = 0.5 * (
            (
                self.L1**2 * p[0] ** 2
                + (1 + self.mass[0] / self.mass[1]) * self.L0**2 * p[1] ** 2
                - 2 * self.L0 * self.L1 * p[0] * p[1] * np.cos(q[0] - q[1])
            )
            * self._kappa(q)
            / (self.L0 * self.L1)
        )
        # Kinetic Energy

        return V_pot + T_kin


class CoupledPendulums(DynamicalSystem):
    """Two coupled pendulums coupled by a spring and moving in 2d plane.

    The two pendulums are suspended from the ceiling, such that their anchor points are
    a distance d_anchor apart. They are coupled by a sprint with spring constant k_spring,
    such that the force between them is zero if they are hanging down vertically. Both pendulums
    have the same mass and are connected to the ceiling by a massless rod of length L_rod.

    If q_0 = theta_0 and q_1 = theta_1 are the angles of the two pendulums, then the positions of
    the masses are:

      q_0 = (L*sin(theta_0), -L*cos(theta_0))
      q_1 = (d+L*sin(theta_1)), -L*cos(theta_1))

    The potential energy is

      V_pot = mass*g_grav*L_rod*( (1-cos(theta_0)) + (1-cos(theta_1)) )
            + 1/2*k_spring*(|q_0-q_1|-d_anchor)^2

    where g_grav is the gravitational acceleration and the kinetic energy is

      T_kin = 1/2*mass*L_rod^2*( (dtheta_0/dt)^2 + (dtheta_1/dt)^2 )
            = 1/(2*mass*L_rod^2) * (p_0^2 + p_1^2)

    In the second line the kinetic energy is expressed in terms of the canonical momenta

      p_0 = mass*L_rod^2* dtheta_0/dt
      p_1 = mass*L_rod^2* dtheta_1/dt
    """

    def __init__(self, mass, L_rod, d_anchor, k_spring, g_grav=9.81):
        """Create new instance of coupled pendulums class

        :arg L_rod: length of rods
        :arg d_anchor: distance between anchor points
        :arg k_spring: spring constant
        :arg g_grav: gravitational acceleration
        """
        super().__init__(2, mass)
        self.separable = True
        self.L_rod = L_rod
        self.d_anchor = d_anchor
        self.k_spring = k_spring
        self.g_grav = g_grav
        # C-code snipped for computing the acceleration update
        self.dH_header_code = """
        #include "math.h"
        """
        self.dH_preamble_code = """
        double phi;
        double sin_q0;
        double sin_q1;
        double cos_q0;
        double cos_q1;
        double C_tmp;
        double sin_q0_q1;
        double z0;
        double z1;
        """
        self.dHq_update_code = f"""
        sin_q0 = sin(q[0]);
        sin_q1 = sin(q[1]);
        cos_q0 = cos(q[0]);
        cos_q1 = cos(q[1]);
        sin_q0_q1 = sin(q[0]-q[1]);
        z0 = {self.d_anchor} + {self.L_rod} * (sin_q1 - sin_q0);
        z1 = {self.L_rod}* (cos_q1 - cos_q0);
        phi = sqrt( z0*z0 + z1*z1 );
        C_tmp = {self.k_spring} * {self.L_rod} * ({self.d_anchor}/phi - 1.0);        
        dHq[0] = C_tmp * ( ({self.d_anchor}) * cos_q0 - {self.L_rod} * sin_q0_q1)
               + {self.g_grav} / {self.L_rod} * sin_q0;
        dHq[1] = C_tmp * ( -{self.d_anchor} * cos_q1 + ({self.L_rod}) * sin_q0_q1)
               + {self.g_grav} / {self.L_rod} * sin_q1;
        """
        self.dHp_update_code = f"""
        dHp[0] = p[0] / ({self.mass}*{self.L_rod}*{self.L_rod});
        dHp[1] = p[1] / ({self.mass}*{self.L_rod}*{self.L_rod});
        """

    def _phi(self, theta_0, theta_1):
        """Compute distance |q_0-q_1| = phi(theta_0, theta_1)

        given by

        phi(theta_0,theta_1) := |q_0-q_1| = sqrt( (d_anchor + L_rod*(sin(theta_1)-sin(theta_0)))^2
                                                + L_rod^2*(cos(theta_1)-cos(theta_0))^2 )

        :arg theta_0: angle of first bob
        :arg theta_1: angle of second bob
        """
        return np.sqrt(
            (self.d_anchor + self.L_rod * (np.sin(theta_1) - np.sin(theta_0))) ** 2
            + self.L_rod**2 * (np.cos(theta_1) - np.cos(theta_0)) ** 2
        )

    def compute_dHq(self, q, p, dHq):
        """Compute dH/dq

        With theta_0 = q[0], theta_1, q[1],
        the (negative) forces are gives:

        dH/dtheta_0 = dV_pot/dtheta_0
            = C * ( d_anchor*cos(theta_0) - L_rod*sin(theta_0-theta_1) )
              + g_grav/L_rod*sin(theta_0)

        dH/dtheta_1 = dV_pot/dtheta_1
            = C * ( - d_anchor*cos(theta_0) + L_rod*sin(theta_0-theta_1) )
              + g_grav/L_rod*sin(theta_1)

        where

        C = k_spring / (L_rod * mass) * (d_anchor-phi(theta_0,theta_1)) / phi(theta_0,theta_1)

        :arg q: angles of bobs wrt vertical (2-dimensional array)
        :arg p: Angular momenta (2-dimensional array)
        :arg dHq: resulting dH/dq
        """
        phi = self._phi(q[0], q[1])
        C_tmp = self.k_spring * self.L_rod * (self.d_anchor - phi) / phi
        dHq[0] = C_tmp * (
            self.d_anchor * np.cos(q[0]) - self.L_rod * np.sin(q[0] - q[1])
        ) + self.g_grav / self.L_rod * np.sin(q[0])
        dHq[1] = C_tmp * (
            -self.d_anchor * np.cos(q[1]) + self.L_rod * np.sin(q[0] - q[1])
        ) + self.g_grav / self.L_rod * np.sin(q[1])

    def compute_dHp(self, q, p, dHp):
        """Compute dH/dp

        dH/dp_j = p_j/(mass*L_rod^2)

        :arg q: angles of bobs wrt vertical (2-dimensional array)
        :arg p: Angular momenta (2-dimensional array)
        :arg dHp: resulting dH/dp
        """
        dHp[:] = p[:] / (self.mass * self.L_rod**2)

    def set_random_state(self, q, p):
        """Draw angles and angular momenta.

        We assume that angles theta_0 and theta_1 stay in the range [-pi/4,+pi/4], and
        that the energy never exceeds the maximum value

        E_{max} = k_spring*L_rod^2 + mass*g_grav*L_rod*(2-sqrt(2))

        :arg q: Angles with vertical (2-dimensional array)
        :arg p: Angular momenta (2-dimensional array)
        """

        # Draw angle
        q[0:2] = np.random.uniform(low=-0.25 * np.pi, high=+0.25 * np.pi, size=(2))
        R_theta = (
            self.mass
            * self.L_rod**2
            * np.sqrt(
                self.k_spring
                / (self.mass * self.L_rod**2)
                * (2.0 * self.L_rod**2 - (self._phi(q[0], q[1]) - self.d_anchor) ** 2)
                + 2.0
                * self.g_grav
                / self.L_rod
                * (np.cos(q[0]) + np.cos(q[1]) - np.sqrt(2))
            )
        )
        p[:] = R_theta
        while p[0] ** 2 + p[1] ** 2 > R_theta**2:
            p[0:2] = np.random.uniform(low=-R_theta, high=R_theta, size=(2))

    def energy(self, q, p):
        """Compute total energy E = V_pot + T_kin

        :arg q: Angles with vertical (2-dimensional array)
        :arg p: Angular momenta (2-dimensional array)
        """
        V_pot = 0.5 * self.k_spring * (
            self._phi(q[0], q[1]) - self.d_anchor
        ) ** 2 + self.mass * self.g_grav * self.L_rod * (
            2 - np.cos(q[0]) - np.cos(q[1])
        )
        T_kin = 0.5 * (p[0] ** 2 + p[1] ** 2) / (self.mass * self.L_rod**2)
        return V_pot + T_kin
