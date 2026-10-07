# Algebraic argument for pinned-share refresh

These are written mathematical arguments, not proof-assistant output. All objects needed below are defined here; the repository does not need a manuscript directory. The claimed newness of the formulation remains unverified. Interpolation, the linear-functional alternative, and shortest-path optimization are standard tools.

## 1. State, probability space, and exposure

Let F be a finite field of size q. A fixed pool X contains n distinct nonzero elements of F. Let 2 <= k <= n and let slots be 0,...,T-1. A valid state in slot e is a polynomial F_e of degree below k with F_e(0)=S. Holder x stores only F_e(x). At boundary e the unavailable set O_e is pinned: F_{e+1}(x)=F_e(x) for x in O_e. A share retained offline must therefore remain a valid *current* evaluation, not merely an old-generation share.

Define Z(O) to be the space of degree-below-k polynomials vanishing at zero and at every point of O. Its dimension is max(k-1-|O|,0). When |O|<k-1, its elements have the unique form

    g(Z) = Z product_{x in O}(Z-x) r(Z),   deg r < k-1-|O|.

Distinct nonzero coordinates make these roots distinct. If |O|>=k-1, the only possible polynomial is zero by the root bound. Uniform setup chooses all nonconstant coefficients of F_0 independently and uniformly. Each update independently chooses G_e uniformly in Z(O_e) and sets F_{e+1}=F_e+G_e.

For a fixed pin sequence, legal polynomial paths with constant term s form an affine space W_s. The map from a path to its initial polynomial and successive differences is bijective. Thus the rule above is uniform on W_s, of cardinality q^D, where D=(k-1)+sum_e max(k-1-|O_e|,0).

In slot e the adversary learns current shares at C_e. Every share observed during an atomic refresh counts in both adjacent slots. Reading an offline holder is allowed; inability to receive a network message does not imply physical unreadability. A passive policy may adapt future sets, stopping decisions, and public metadata to its preceding permitted view and secret-independent public coins. It may not inspect an unseen secret value to choose metadata. During one atomic protocol refresh the corrupt participant set is fixed. Honest parties really erase old shares, seeds, and intermediate messages, and channels are ideal private channels. These are assumptions, not conclusions about implementation.

## 2. Exact trace alternative and scalar adaptive leakage

For fixed C and O, secrecy of the uniform rule is equivalent to existence of polynomials h_e of degree below k satisfying

    h_e(0)=1;   h_e(x)=0 for x in C_e;
    h_{e+1}(x)=h_e(x) for x in O_e.

To prove sufficiency, translation F_e -> F_e+(s'-s)h_e maps each legal path with secret s to a legal path with secret s' and the same observations. Its inverse uses s-s'. Uniform path sampling gives equal probabilities of every observation under all secrets.

For necessity let W be the vector space of all legal paths with an unrestricted common constant term. Let ell:W->F give that constant and M:W->F^m give the observation vector. A hiding path is an element of ker M with ell(h)=1. If none exists, ell is zero throughout ker M, since any nonzero ell value could be normalized. Therefore phi(Mw)=ell(w) is well defined on im M. Extend phi linearly to the ambient observation space. Some row beta represents it, so ell(w)=beta M w on every legal path. The observations reconstruct S.

In an ambient coefficient vector z=(S,a_0,1,...,a_{T-1,k-1}), write Pz=0 for all pin equations and Az for observations. The same factorization gives

    (1,0,...,0) = alpha P + beta A.

The alpha terms are zero constraints, not additional leaked random values. This identity is directly checkable on coefficient basis vectors. The alternatives are exclusive because applying a supposed revealing identity to a normalized hiding path yields 1=0. This also proves a distribution-independent lower bound: when no hiding path exists, *any* valid pin-preserving update rule reveals S on that trace. Uniform constrained refresh attains privacy on every trace for which privacy is possible in this class. No entropy- or communication-optimality result is implied.

For an adaptive policy, include its public coins, chosen sets, stopping decisions, and observations in a complete leaf v. After fixing coins, that leaf specifies a fixed sequence of linear constraints and pin spaces. Each compatible path has the same probability q^{-D_v}; different leaves may have different D_v. Translation by a leaf's hiding path preserves each observed prefix and consequently every choice the policy makes. A hiding leaf has the same probability for every secret. A revealing leaf determines the secret uniquely by its linear identity.

For uniform S, a nonempty leaf consequently has either a uniform posterior over F or a point posterior. Let p be the revealing-leaf probability. The sum of probabilities of hiding leaves is the same under each fixed secret; its complement p is therefore also the same. For two different fixed secrets, their distributions coincide on all hiding leaves and have disjoint support on revealing leaves. Hence TV(View_s,View_s')=p. Conditional entropy is (1-p) log2(q), so I(S;View)=p log2(q). Binary discrimination with equal prior succeeds with probability (1+p)/2. These are scalar linear-view statements, not a general claim about vector secrets or nonlinear leakage.

## 3. Capacity and interval partitions

Let b_e and u_e be nonnegative integer bounds on |C_e| and |O_e|. For the storage interpretation they are at most n. Set

    L_0=0,       L_{e+1}=min(u_e,L_e+b_e);
    R_{T-1}=0,   R_e=min(u_e,R_{e+1}+b_{e+1});
    Gamma=max_e (b_e+L_e+R_e).

Gamma is an uncapped budget capacity. When Gamma>n, only n distinct party labels can be instantiated. All secrecy decisions below compare it with k<=n.

Write B_j=sum_{e<j} b_e. Cuts range from 0 to T. Set c_0=c_T=0 and c_j=u_{j-1} at internal cuts. A nonempty interval [a,z) has weight

    w(a,z)=B_z-B_a+c_a+c_z.

A partition 0=t_0<...<t_r=T has width max_i w(t_{i-1},t_i). Let W be the minimum width. Then **W=Gamma**.

First, expanding the recurrences by induction gives

    L_e=min_{a<=e}(B_e-B_a+c_a),
    R_e=min_{z>e}(B_z-B_{e+1}+c_z).

Adding these independent minima gives b_e+L_e+R_e=min_{a<=e<z} w(a,z). Every partition has an interval covering e, so W>=Gamma.

For the other direction, the key uncrossing identity for a<c<b<d is

    w(a,c)+w(b,d)=w(a,b)+w(c,d)-2(B_b-B_c).

Because b_e>=0, if both crossing intervals have weight at most H, at least one of the two intervals on the left also has weight at most H.

Set H=Gamma and create an edge a->z whenever a<z and w(a,z)<=H. The pointwise minimum says every slot is covered by some edge interval. Suppose T is unreachable from 0. Let m<T be the largest reachable cut, and fix a path to m. An edge c->d covering slot m has c<=m<d. If c is on the path, extend it to d, contradicting maximality of m. Otherwise c lies strictly inside a path edge a->b, so a<c<b<=m<d. Uncrossing yields a->c or b->d. In the first case a path reaches d via c; in the second it reaches d directly from b. Again this contradicts maximality of m. Therefore T is reachable and W<=H. This proves the identity without bounded enumeration.

A bottleneck recurrence D_0=0 and D_z=min_{a<z} max(D_a,w(a,z)) constructs a partition. Prefix sums and predecessor pointers give an O(T^2) arithmetic implementation. The capacity alone uses two O(T) recurrences. The bounded repository implementation prepares prefix sums but retains simple full paths, whose copying still gives O(T^3) in its unrestricted asymptotic interpretation. The public direct interval sum and independent enumeration are unchanged.

## 4. Exact worst-case secrecy and recovery

**The frontier is Gamma<k.** For sufficiency take a partition of width Gamma. For each interval I=[a,z), let U_I be the union of all C_e within I and the pin sets at its two external boundaries, omitting a missing outer boundary. Its size is at most w(a,z)<k. Set

    h_I(Z)=product_{x in U_I}(1-Z/x),

and use that polynomial in every slot of I. The constant term is one, all exposed coordinates are roots, and its degree is below k. Internal pin equalities hold because the same polynomial is used on both sides. At a partition cut both neighboring polynomials vanish on the cut's actual pin set. This is a hiding path. The same public partition works on every adaptive leaf, so the adaptive alternative proves complete-view secrecy in the ideal observation model.

For necessity choose a pivot p with b_p+L_p+R_p>=k. Use c=min(b_p,k) labels observed at p, a=min(L_p,k-c) distinct left labels, and d=k-c-a distinct right labels. The inequality ensures d<=R_p. All k labels can be distinct because k<=n.

To transport the a left labels to p, work backward. If a'<=L_{e+1} labels must reach the next slot, pin those a' at boundary e, observe min(b_e,a') of them at slot e, and continue backward with the remainder. The recurrence ensures a'<=u_e and max(a'-b_e,0)<=L_e. At slot 0 nothing remains unassigned since L_0=0. The right labels are assigned symmetrically forward from p: pin each until its future observation, and remove it from the needed list then. The right recurrence enforces every boundary and slot budget. Left and right constructions use disjoint time sides, so their pin requirements do not add at any one boundary.

Each retained observation is F_p(x) at its coordinate by its chain of pin equalities. Lagrange interpolation on these k distinct points recovers

    S=sum_x F_p(x) product_{y!=x} (-y)/(x-y).

This holds for every polynomial-valid pin-preserving update rule and any sampling distribution. It is a fixed permitted trace, not an attack on an external system.

For cooperative recovery, k distinct current shares always interpolate. Requiring recovery at the uniform initial slot with at most u_rec unavailable holders is possible exactly when k<=n-u_rec. Necessity follows because fewer than k initial shares have identical distributions under every secret: the root polynomial construction supplies a secret-shifting bijection. This does not lower-bound schemes with extra recovery state, nor does it handle withholding or incorrect replies.

Thus both properties require Gamma<k<=n-u_rec together with the standing k>=2 convention. Equivalently, the legal integer set begins at max(2,Gamma+1) and is nonempty exactly when that value is at most n-u_rec.

For constant b and u, L_e=min(eb,u) and R_e=min((T-1-e)b,u). A central pivot maximizes their sum, giving

    Gamma_T=b+min(floor((T-1)/2)b,u)+min(ceil((T-1)/2)b,u)
           =min(Tb,ceil(T/2)b+u,b+2u).

The equality follows by separating odd T=2m+1 and even T=2m and considering where u lies relative to mb and (m-1)b. With b>0 the value reaches b+2u once T>=2ceil(u/b)+1. With b=0 it is always zero, not 2u.

If the same actual set O is pinned throughout and |O|<=u, the capacity is min(sum b_e,u+max b_e). For secrecy, either one normalized polynomial vanishes on all observations, or each slot's normalized polynomial vanishes on O union C_e. These work when the first or second term, respectively, is below k. Conversely choose a maximum-budget slot, read min(b_p,k) coordinates there, and pin the remaining k-c coordinates throughout. They fit in u and can be observed across the other slots because total exposure is at least k. Interpolation again recovers S.

A wall-clock cadence additionally needs a declared bound B(Delta) on lifetime distinct-share exposures in a period of length Delta. Substitute b=B(Delta) into the finite-horizon formula; an instantaneous corruption bound is not a valid replacement. No value of B(Delta) is empirically measured here.

## 5. Derived parameter rules and audit certificates

Because Gamma equals the minimum partition width, it is monotone in every budget. Increasing one slot budget by delta raises the weight of exactly one interval in a fixed partition by delta. Increasing one internal boundary budget affects only partitions cutting there and raises each adjacent interval weight by delta, so their maximum rises by at most delta. Taking the minimum over partitions preserves both statements. Applying this one coordinate at a time gives

    |Gamma(b,u)-Gamma(b',u')|
      <= sum_e |b_e-b'_e| + sum_e |u_e-u'_e|.

Thus an integer margin m=k-1-Gamma tolerates any collection of budget increases of total L1 size at most m. This is a deterministic worst-case margin, not a probability.

The standing model requires k>=2. Hence the smallest legal secret threshold is

    k_min=max(2,Gamma+1).

Combining this with cooperative recovery yields the exact integer set

    max(2,Gamma+1) <= k <= n-u_rec.

It is feasible exactly when the lower endpoint does not exceed the upper endpoint; otherwise the set is empty. In particular, zero exposure gives Gamma=0 but never recommends k=1.

For constant positive b, the three branches of

    Gamma_T = min(Tb, ceil(T/2)b+u, b+2u)

have explicit regimes. The horizon branch is minimal iff u>=floor(T/2)b. The local two-boundary branch is minimal iff u<=(ceil(T/2)-1)b. The balanced branch is minimal between those bounds. For odd T the balanced branch appears only at a tie; for even T it occupies a band of width b.

The formula can be inverted. If b+2u<k, every finite horizon is safe. Otherwise let

    H1=floor((k-1)/b),
    H2=2 max(0,floor((k-1-u)/b)).

A positive horizon is safe exactly when T<=max(H1,H2). This follows because, when the long-horizon branch is unsafe, secrecy is the union of the two integer inequalities Tb<k and ceil(T/2)b+u<k.

The frontier has short two-sided audit evidence. A safe certificate is an interval partition whose weights are all below k; prefix sums verify it in linear time. An unsafe certificate names a target slot and at most k distinct coordinate labels, each with its observation slot and consecutive pin range to the target. Checking observation budgets, pin budgets, path contiguity, and the target Lagrange identity verifies one reconstructing trace. Duality and the transport construction guarantee that exactly one certificate type exists for each public-budget instance.

As a heterogeneous example, b=(1,3,0,2,1) and u=(2,1,3,1) give L=(0,1,1,1,1), R=(2,1,3,1,0), and local totals (3,5,4,4,2). Hence Gamma=5. Cuts (0,2,4,5) have weights (5,4,2), while the lower construction carries one earlier and one later value to the three observations in slot 1. Threshold six is the smallest universally secret choice; with n=10 and u_rec=3, thresholds six and seven are jointly feasible.

## 6. Minimum-cost robust offline schedule

At each internal boundary j, refreshing costs a_j>=0 and has pin budget u_{j-1}. A skipped refresh preserves the entire polynomial, equivalent to pinning all n coordinates. For an actual refresh set R, define u^R_{j-1}=u_{j-1} when j is in R and n otherwise. The frontier proves that R is universally safe iff Gamma(b,u^R)<k. For necessity, strengthen the lower witness's skipped-boundary pin sets to all of X; every interpolation equality path remains valid.

Without policy constraints, create edges a->z with w(a,z)<k. Entering internal cut z costs a_z; entering T costs zero. A path's internal cuts Q define a safe actual schedule R=Q. Conversely, any safe R has a width-below-k partition for u^R. Its internal cuts Q satisfy Q subseteq R because a cut at a skipped boundary would contribute n>=k. Changing every refresh in R minus Q into a skipped boundary leaves that same partition valid. Nonnegative costs make Q no more expensive than R, so a shortest path minimizes cost. If no path exists, the all-refresh capacity is at least k and its transport witness survives any additional skipped boundaries.

With allowed set A and mandatory set M subseteq A, the actual schedule and the certificate cuts must be distinguished. A feasible actual set satisfies M subseteq R subseteq A, while the certificate needs only Q subseteq R. Prepay sum_{j in M} a_j, exclude cuts outside A, do not force the path to visit M, and charge only a_j for entered nonmandatory cuts. Return R=M union Q. A path Q is safe because every one of its cuts is refreshed in R. Conversely, a safe feasible R has some Q subseteq R; replacing R by M union Q preserves the partition, remains feasible, and cannot increase cost. This proves optimality.

A refresh-count cap must count |R|=|M union Q|=|M|+|Q minus M|, not the number of path vertices. A layered graph can track that quantity. Failure under such a cap proves that no policy-feasible actual subset has a safe partition; it need not yield one common transport witness unless even refreshing every allowed boundary is unsafe.

The smallest regression is over F_7 with n=5, k=4, b=(2,1), u=(2), and the unique boundary mandatory at charge one. The actual R={1} has Gamma=3. Its certificate uses Q empty and the one interval of weight three. Forcing the mandatory boundary into Q would instead create weights four and three and incorrectly reject a safe schedule.

## 7. Passive protocol and full refresh-message simulation

At a boundary let P=X minus O be the online set and V=Z(O). Every online dealer j independently samples g_j uniformly in V and sends g_j(x) privately to each online recipient x. Each recipient adds all received contributions; offline holders keep their values. The aggregate G=sum_j g_j belongs to V, so correctness and all pins hold. Its distribution is uniform when one summand is uniform. Privacy of the full corrupt view requires at least one honest online dealer whenever V is nonzero; the zero-space case needs no entropy.

Fix the corrupt online recipients B and let E:V->F^B be evaluation there, with image W. The simulator receives their ideal old and new shares, so it knows E(G). A corrupted dealer's fresh polynomial can be sampled independently and uniformly from V even conditional on the aggregate G: the honest sum is uniform and masks every fixed corrupt contribution tuple. Let C be the sum of those sampled corrupt polynomials.

Suppose h>=1 dealers are honest. Sample h-1 independent uniform vectors from W and make the last E(G-C) minus their sum. These are the simulated honest messages to the corrupt recipients. To prove their distribution, condition h independent uniform polynomials in V on their sum v=G-C. For any image tuple in W^h summing to E(v), choose arbitrary lifts of its first h-1 vectors, then the last polynomial is forced. There are exactly |ker E|^{h-1} choices, independently of the tuple. Thus every permitted image tuple has equal conditional probability, exactly as the simulator produces. Sampling in the image W, rather than arbitrary independent field coordinates, is essential when evaluation coordinates are dependent.

The distributional statement holds conditional on the entire aggregate polynomial, not just its observed evaluations. It therefore remains valid if later ideal shares reveal more of that aggregate. Corrupt dealers' outgoing messages are determined by their sampled polynomials; all other corrupt local quantities follow from already supplied shares and incoming messages. Messages between honest participants are not visible on ideal private channels.

Compose across atomic boundaries by induction on actions. An ordinary observation supplies the same ideal current share. When V is zero-dimensional, all dealer polynomials and messages are zero and are simulated directly, even with no honest online dealer. Otherwise the honest-dealer assumption ensures h>=1 and the conditional simulator above gives exactly the real corrupt-message distribution. After release, the honest participant resumes the prescribed fresh-randomness behavior; before later corruption it has erased obsolete shares, randomness, and transient messages. A newly corrupted participant consequently reveals only current state already represented by the ideal interface, not a previously simulated honest seed. Policy decisions based on the full transcript preserve the induction because the transcripts agree in distribution. No secret or unobserved share is used to generate the extra simulated information.

This proves perfect passive complete-view simulation in the stated atomic, private-channel, trusted-erasure model. It is not a malicious or universally composable protocol proof and it does not construct secure erasure.

Finally, a public classical transcript alone cannot certify deletion of freely copyable private state. A participant can copy the state into a hidden register and execute the prescribed deletion on the original with exactly the honest coins. Public transcripts are identical while the copy survives. The claim applies only to this classical unrestricted-copy model, not to quantum deletion or trusted hardware.

## 8. What executable checks add

The certificate checker evaluates polynomials or coefficient-basis identities without the producer's elimination. The direct oracles enumerate actual random choices and compare secret-conditioned histograms. The trace-level transport helper follows pins and checks Lagrange coefficients only; the budget-level wrapper additionally binds the trace to the original b, u, threshold/capacity pair, and explicit coordinate pool. Controlled pin-count, exposure-count, and threshold mutations must be rejected there even when the underlying algebraic path remains valid.

The small public-budget oracle first rank-tests each concrete set system, then applies a componentwise prefix OR to exact count vectors. Its claim is existential: a revealing trace exists within a budget iff Gamma>=k. It does not classify every trace by its dominating budget. The F_5 trace C_0=C_1=O_0={1} with n=3 and k=2 is a retained hiding regression (h_0=h_1=1-Z) even though the count budget has Gamma=2. Scheduler comparison enumerates actual refresh subsets and evaluates Gamma(b,u^R), including mandatory and count-cap constraints.

The 6,820 fixed-pin items compare the helper against the same displayed formula and are implementation-consistency regressions, not an independent secrecy oracle. A separate local-rank enumeration holds one identical actual O at every boundary and compares revealing existence with the fixed-pin formula on 5,120 concrete systems and 253 budgets. The horizon inversion regression covers only b=1..4, u=0..4, k=2..12 (220 tuples), with a bounded scan through T=12; no all-supported-input claim is made.

The simulator control enumerates real and ideal local tuples. Each check targets a different mistake, but all share an authored model and are not independent scientific reviewers. None of these bounded computations proves the general quantifiers above or resolves novelty against unread literature.
