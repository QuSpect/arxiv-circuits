# arxiv-circuits

**arXiv quant-ph 近期论文中的关键量子线路（OpenQASM 2.0）。**

[English](README.md)

本数据集包含 **55 条量子线路**，来自 **41 篇** 2026-06-28 至 2026-10-28 期间提交到 arXiv quant-ph
（主分类或交叉投稿）的论文。每条线路都从论文 LaTeX 源码中的 quantikz / qcircuit 线路图逐门读出，
与论文内容核对后保存为独立的 OpenQASM 2.0 文件。manifest 把每条线路与原论文对应起来，并记录验证方式。

这些线路是论文提出、构造或作为主要研究对象的线路——算法、拟设、编码、分解、模拟步、态制备与算术
线路，规模为 3 到 16 个比特，可用作量子编译器、模拟器和线路分析工具的真实、较新且来源独立的测试输入。

本数据集最初是为 [quspect](https://github.com/QuSpect/quspect) 的编译 benchmark 构建的。

## 内容

```
circuits/           55 个 OpenQASM 2.0 文件
manifest.csv        每条线路一行（与 manifest.jsonl 内容相同）
manifest.jsonl
review_log.jsonl    全部审核决定（收录与拒收）及原因
tools/              提取流水线与测试（MIT 许可证）
LICENSE             CC BY 4.0（数据与文档）
CITATION.cff
```

## 收录规则

- **只收精确来源**：线路逐门取自论文 LaTeX 源码中的 quantikz / qcircuit 线路图（或正文中的
  OpenQASM 代码）。不根据文字描述重构，不从图片转录，不拼接多张图。论文附带代码仓库中没有找到属于
  论文本身的 `.qasm`（唯一一个带 `.qasm` 的仓库是 QASMBench 原样拷贝）。
- **只收具体线路**：含抽象方框（U、W、QFT、PREP、oracle 等）、省略号（`\vdots`/`\cdots`，即通用
  n 比特模板）、一根线代表多个比特、或只是片段的线路图一律不收。
- **去掉测量，保留酉部分**：末端和中途测量都删除；依赖中途测量/重置/经典反馈才有意义的线路（如综合征
  提取 gadget）不收；由输入态 `|1⟩`/`|+⟩`/`|−⟩` 标注的输入补上对应的 X/H。
- **是论文的关键线路**：论文提出、构造或作为主要对象使用的线路；论文中顺带出现的教科书小 gadget
  （Bell/GHZ 制备、通用 QFT 示意、门恒等式）不收。每篇最多 3 条，且须结构不同（同一模板只留最有
  代表性的一条）。
- **规模下限**：≥ 3 比特，分解到 CNOT + 单比特门后 ≥ 6 个 CNOT。
- **参数**：论文给出具体角度时用论文值；否则每个符号角度取由符号名确定的伪随机值（符号名的 SHA-256
  映射到 [−π, π)，保留 6 位小数），固定且可复现，见 `params_source`。角度取值不影响线路结构。

## 验证

每条线路都经过：

1. **逐门核对**：转换结果与 LaTeX 原图逐门比对（控制/开控制/目标/旋转轴/线序）。
2. **酉等价断言**：规范化后的 QASM 与解析出的原图线路酉等价（翻译时不借用空闲比特作 |0⟩ 辅助比特）。
3. **功能验证**：在最终 QASM 上模拟，核对论文对该线路的描述（制备的态、实现的酉/相位、真值表、论文
   给出的门数等），结果写在 `verification` 字段；无法做功能核对的写为 `faithfulness only`。
4. **复核**：发布前用转换器从论文源码重新生成每条线路，与审核产出的文件做酉等价比对，并检查 qiskit、
   pytket、quspect 都能读入。

所有审核决定（含拒收及原因，也包括转换器修正前的旧版本候选）见 `review_log.jsonl`。

## 筛选漏斗

| 阶段 | 数量 |
|---|---|
| quant-ph 论文（含交叉投稿） | 8158 |
| 关键词粗筛（circuit/qubit/gate/algorithm 等） | 4983 |
| 已下载 LaTeX 源码 | 3411 |
| 源码含 quantikz/qcircuit/OpenQASM | 448 篇，1514 张图 |
| 无抽象门、可精确转换 | 441 张 |
| 达到规模下限的候选 | 141 张 |
| 逐条审核 | 141 条 |
| 收录 | 55 条（41 篇） |

2026-08-28 至 10-28 下载了全部关键词命中论文；2026-06-28 至 08-27 只下载了标题或摘要含 circuit 的
688 篇（先处理的 08-28 至 10-28 时段 25 篇收录论文中有 24 篇属于这一组，其余论文 arXiv 下载很慢且产出极低）。

多数论文无法贡献线路的主要原因：线路图是预先渲染的 PDF/PNG 图片（源码中没有线路描述），或使用
抽象方框/省略号表示通用结构，按“只收精确来源”的规则无法收录。

## 文件格式

**QASM 文件**（`circuits/*.qasm`）：

- OpenQASM 2.0，`include "qelib1.inc";`，单个 `qreg q[n];`，无经典寄存器，无测量和 barrier。
- 门限定为 `id h x y z s sdg t tdg rx ry rz p u3 cx cz cp crz swap ccx`（qiskit、pytket、quspect
  等常见 OpenQASM 2.0 读入器都支持）；`ccx` 作为原生门保留。角度单位为弧度。不表示全局相位。
- `q[0]` 是线路图中最上面的一根线，向下依次编号；图中空闲的线被删除。这可能与论文自己的比特标号
  不同（相关情况在 `review_log.jsonl` 中注明）。
- 命名：`arxiv<arXiv 编号>_<名称>_<比特数>.qasm`。

**Manifest**（`manifest.csv` / `manifest.jsonl`，内容相同，按论文从新到旧）：

| 字段 | 含义 |
|---|---|
| `file` | `circuits/` 中的文件名 |
| `arxiv_id` | arXiv 编号（含线路所取自的版本号） |
| `url` | `https://arxiv.org/abs/<arxiv_id>` |
| `title` | 论文题目 |
| `submitted` | 首次提交日期（YYYY-MM-DD） |
| `primary_category` | arXiv 主分类 |
| `description_zh` | 一句话描述（中文） |
| `description_en` | 一句话描述（英文） |
| `category` | `algorithm`、`ansatz`、`arithmetic`、`decomposition`、`simulation`、`state_prep` 或 `other` |
| `n_qubits` | 比特数 |
| `n_2q` | 文件中的两比特门个数（`cx`、`cz`、`cp`、`crz`、`swap`） |
| `n_ccx` | `ccx` 门个数 |
| `n_2q_ccx6` | `n_2q + 6 * n_ccx`（Toffoli 按 6 个 CNOT 计） |
| `depth` | 文件按原样计算的线路深度（每个门计一层，含 `ccx`），即 qiskit `QuantumCircuit.depth()` |
| `source` | 线路图类型及其在论文源码所有线路图中的序号 `k`（对应 `review_log.jsonl` 的 `diagram`） |
| `params_source` | 角度取值来源 |
| `verification` | 核对内容与结果 |
| `flags` | 转换器标记，如 `measure_dropped` |

**审核记录**（`review_log.jsonl`）：每张审核过的线路图一条记录，字段为 `arxiv_id`、`title`、
`diagram`（序号 `k`）、`decision`（`accept` / `reject`）和 `reason`。

## 使用

用 qiskit：

```python
import json
from qiskit import QuantumCircuit

rows = [json.loads(line) for line in open("manifest.jsonl", encoding="utf-8")]
for row in rows:
    qc = QuantumCircuit.from_qasm_file(f"circuits/{row['file']}")
    assert qc.num_qubits == row["n_qubits"] and qc.depth() == row["depth"]
print(len(rows), "circuits loaded")
```

用 [quspect](https://github.com/QuSpect/quspect)（`pip install quspect`）：

```python
from pathlib import Path
from quspect.ir import qasm2_loads

circ = qasm2_loads(Path("circuits/arxiv2610.25350_su3_singlet_prep_6.qasm").read_text())
print(circ.num_qubits, len(circ))  # 6 个比特，14 条指令
```

检查整个数据集（由 QASM 重新计算 manifest 统计量、门集、链接、读入）：

```bash
pip install -r tools/requirements.txt
python -I tools/check_dataset.py
```

## 复现提取流程

完整流水线（arXiv 元数据与源码下载、线路图转换、审核分批、汇总）在 [`tools/`](tools/) 中，说明见
[`tools/README.md`](tools/README.md)，审核规范见 [`tools/REVIEW_BRIEF.md`](tools/REVIEW_BRIEF.md)。
转换器测试：`python -I tools/tests/run_all.py`。

## 许可证

- **数据与文档**——QASM 文件、`manifest.csv`、`manifest.jsonl`、`review_log.jsonl` 及文档——采用
  [知识共享署名 4.0 国际许可协议（CC BY 4.0）](LICENSE)。
- [`tools/`](tools/) 下的**代码**采用 [MIT 许可证](tools/LICENSE)。

这些线路是从各论文 LaTeX 源码的线路图中逐门读出的门序列，是对论文所给线路的事实性描述，每条都附有
原文链接；本仓库不转载论文正文、图片或 LaTeX 源码。原论文版权归各自作者所有。**使用某条线路时，请同时
引用其原论文**（见 `arxiv_id` / `url`）和本数据集。

## 引用

见 [`CITATION.cff`](CITATION.cff)：

```bibtex
@misc{arxiv_circuits_2026,
  author       = {Xu, Xusheng and {QuSpect}},
  title        = {arxiv-circuits: Key quantum circuits from recent arXiv quant-ph papers},
  year         = {2026},
  version      = {1.0.0},
  howpublished = {\url{https://github.com/QuSpect/arxiv-circuits}}
}
```

## 线路

按论文提交时间从新到旧。

<!-- circuits-table:start -->
| 文件 | arXiv | 论文题目 | 描述 | 比特 | 2q | ccx | 深度 |
|---|---|---|---|---|---|---|---|
| `arxiv2610.37247_elastic_wave_directional_block_3d_4.qasm` | [2610.37247v1](https://arxiv.org/abs/2610.37247v1) | Quantum circuits of elastic wave equations via Schrödingerisation | 在 4 个分量比特上实现三维弹性波方程 Schrödinger 化后方向块 e^{iÃ₂t} 的精确线路：先用多控 R_y Givens 旋转（P_ℓ）变换法向应力子空间，再以多控 R_x 实现法向-速度与两个剪切-速度二能级旋转，最后逆变换。 | 4 | 152 | 0 | 231 |
| `arxiv2610.33188_hamming_weight_one_hot_counter_7.qasm` | [2610.33188v1](https://arxiv.org/abs/2610.33188v1) | Quantum Heuristic Separation of Comb Inequalities for the Travelling Salesman Problem | 在 3 个数据比特和 4 个计数比特上，以受控 SWAP（Fredkin）级联把数据寄存器中 \|1⟩ 的个数（汉明重量）编码为计数寄存器的独热态，是梳不等式分离算法中多控 E 门的分解。 | 7 | 12 | 6 | 16 |
| `arxiv2610.31330_qsvt_sign_phase_gadget_6.qasm` | [2610.31330v1](https://arxiv.org/abs/2610.31330v1) | Quantum Fokker-Planck solvers as trainable generative models | 在 4 个标志比特、1 个辅助比特 p 和 sgn 比特上实现 QSVT 相位门 Φ_k：用 4 重开控 Toffoli 在成功子空间翻转 p，施加 R_ZZ(2φ_k) 后反计算，使 sgn=0/1 分别获得 ±φ_k 相位。 | 6 | 41 | 0 | 108 |
| `arxiv2610.30315_deutsch_jozsa_n4_clifford_t_4.qasm` | [2610.30315v1](https://arxiv.org/abs/2610.30315v1) | Normal-Form Characterization of Adaptivity and Entanglement in Pauli-Based Computation | 在 4 个比特上求解一个 Deutsch–Jozsa 问题实例的 Clifford+T 线路：Hadamard 层后接由 7 个 T 门分解的 Toffoli 与一个 CNOT 组成的平衡函数 oracle，再做 Hadamard。 | 4 | 7 | 0 | 14 |
| `arxiv2610.28993_all_to_all_rzz_phi2_5q_5.qasm` | [2610.28993v1](https://arxiv.org/abs/2610.28993v1) | Digital Quantum Simulation of Dynamics in Interacting Fields | 在 5 个比特上用最近邻 CNOT 阶梯实现 Φ²₅(θ)：依次构造各比特对的奇偶并施加 R_Z，从而一次性实现全部 10 个两体 R_ZZ(θ_ab) 旋转。 | 5 | 20 | 0 | 21 |
| `arxiv2610.28349_beam_splitter_v_even_block_4.qasm` | [2610.28349v1](https://arxiv.org/abs/2610.28349v1) | CO$Φ$ - COmpiling PHotonics into dIgital quantum circuits | 在两模截断光子编码（4 比特）上实现优化分束器中的 V_even 块：受控 Y 与 R_x 基变换夹着两组 R_y(ξ±)–CNOT 均匀受控旋转，作用于偶光子数扇区（U₂、U₄）。 | 4 | 10 | 0 | 19 |
| `arxiv2610.28349_beam_splitter_v_odd_block_4.qasm` | [2610.28349v1](https://arxiv.org/abs/2610.28349v1) | CO$Φ$ - COmpiling PHotonics into dIgital quantum circuits | 在两模截断光子编码（4 比特）上实现优化分束器中的 V_odd 块：由 R_x 基变换、受控 Y 门和受控 R_y(−2θ)、R_y(−4θ) 组成，作用于奇光子数扇区（U₁、U₃、U₅）。 | 4 | 6 | 0 | 14 |
| `arxiv2610.28349_truncated_beam_splitter_u1_block_4.qasm` | [2610.28349v1](https://arxiv.org/abs/2610.28349v1) | CO$Φ$ - COmpiling PHotonics into dIgital quantum circuits | 在两模光子各截断为 4 能级（每模 2 比特）的编码下，实现分束器单光子扇区 U₁ 的线路：CNOT 基变换后施加开/闭混合三控 R_y(2θ)，只在 {\|0,1⟩,\|1,0⟩} 子空间做旋转。 | 4 | 22 | 0 | 30 |
| `arxiv2610.25350_su3_singlet_prep_6.qasm` | [2610.25350v1](https://arxiv.org/abs/2610.25350v1) | Real-time quantum simulation of hadron production in deep inelastic scattering | 在 6 个比特上制备 SU(3) 色单态的态制备线路：先用 R_y(θ₁)、受控 R_y(π/2) 和开控 Toffoli 在夸克寄存器上制备 W₃ 态，再用 CNOT 与反夸克寄存器纠缠。 | 6 | 4 | 1 | 8 |
| `arxiv2610.24426_iqp_embedding_layer_4q_4.qasm` | [2610.24426v1](https://arxiv.org/abs/2610.24426v1) | Margin-Based Generalization for Quantum Machine Learning with Classical Data Encoding | 在 4 个比特上实现一层 IQP 数据编码：先对各比特施加 H 与 R_Z(x_i)，再在相邻比特对上施加 R_ZZ(x_i x_{i+1})。 | 4 | 3 | 0 | 6 |
| `arxiv2610.17470_su3_glueball_interaction_givens_3.qasm` | [2610.17470v1](https://arxiv.org/abs/2610.17470v1) | Time-Domain Observables for Resonant Scattering in Quantum Simulations of Lattice Gauge Theory | 在 3 个比特上实现 SU(3) 胶球玩具模型相互作用项 e^{-iθ(\|010⟩⟨101\|+h.c.)} 的线路：先用两个 CNOT 做基映射，再以两个 RCCX（相对相位 Toffoli）与单比特旋转实现双控 R_x 的 Givens 旋转，最后逆映射。 | 3 | 10 | 0 | 26 |
| `arxiv2610.12148_qnn_angle_enc_allpairs_crx_4.qasm` | [2610.12148v1](https://arxiv.org/abs/2610.12148v1) | Large-Scale Benchmarking of Quantum Neural Network Configurations for Financial Time Series Forecasting | 4 比特量子神经网络线路：先用 H 与 R_Y 做角度编码，再施加一层全连接的受控 R_X 拟设（12 个 CRX，覆盖所有有序比特对）。 | 4 | 12 | 0 | 18 |
| `arxiv2610.09141_cognitive_encoder_readout_cry_star_6.qasm` | [2610.09141v1](https://arxiv.org/abs/2610.09141v1) | A Cognitive-Aware QML-CRL Framework for Detecting Affinity and Romance-Investment Fraud | 欺诈检测量子认知编码器的读出块：先在框架比特 q4 上做可训练 RY(μ) 基变换，再用五个受控 RY(φ_j) 把各偏置比特 q0–q4 的信息聚合到叙事比特 q5 上。 | 6 | 5 | 0 | 15 |
| `arxiv2610.06448_hubbard_pair_spin_init_12.qasm` | [2610.06448v2](https://arxiv.org/abs/2610.06448v2) | A Practical Introduction to VQE: Methods, Challenges, and Applications in Physics and Chemistry | 为 6 格点 Hubbard 链（12 个 JW 比特，前 6 个自旋向上、后 6 个自旋向下）制备“配对-自旋”初态：每对相邻格点处于 (\|↑↓⟩+\|↓↑⟩)/√2 叠加，保证半填充且 S_z=0。 | 12 | 9 | 0 | 4 |
| `arxiv2610.05222_bcfe_bell_part_3q_6.qasm` | [2610.05222v1](https://arxiv.org/abs/2610.05222v1) | Efficient Fidelity Estimation of General Quantum Resource States via Clifford Circuits | Bell–相干保真度估计（BCFE）的 Bell 部分：在两组 3 比特上各制备一份 CZ 连接的 RZ(α_jθ)\|+⟩ 资源态，再用横向 CNOT 与 H 做逐对 Bell 测量以估计反对称（单态）事件概率。 | 6 | 7 | 0 | 6 |
| `arxiv2610.05086_jaqsi_pulse_benchmark_crx_ring_n3_3.qasm` | [2610.05086v1](https://arxiv.org/abs/2610.05086v1) | JAQSI: Just Another Quantum Simulator | JAQSI 脉冲级基准线路（n=3）：先在每个比特上作用 H 门，再施加首尾相接的 CRX(φ) 环（0→1、1→2、2→0）。 | 3 | 3 | 0 | 8 |
| `arxiv2610.04731_phase_gradient_injection_l3_7.qasm` | [2610.04731v1](https://arxiv.org/abs/2610.04731v1) | Sum-of-squares compilation of matrix-model dynamics for NISQ and fault-tolerant hardware | 相位梯度注入线路：用 Cuccaro 加法器把 2 比特数值寄存器 V（零扩展到 3 比特）加到 3 比特催化相位梯度寄存器 \|γ_L⟩ 上，从而施加相位 e^{−2πiV/2^L} 且 \|γ_L⟩ 与辅助比特保持不变。 | 7 | 12 | 6 | 16 |
| `arxiv2610.04731_free_abs_value_q3_7.qasm` | [2610.04731v1](https://arxiv.org/abs/2610.04731v1) | Sum-of-squares compilation of matrix-model dynamics for NISQ and fault-tolerant hardware | 对 3 比特整数 n 编码的奇数 m=2n−7 计算绝对值 \|m\| 的可逆线路：用临时比特保存 ¬MSB(n)，把 n 的低位上移一位并按符号条件取反写入输出寄存器，最低位恒置 1，最后恢复临时比特。 | 7 | 6 | 0 | 6 |
| `arxiv2610.03686_aim_onebody_target_action_6.qasm` | [2610.03686v2](https://arxiv.org/abs/2610.03686v2) | Efficient Block Encoding of Structured Hamiltonians by Separating Where and What | Anderson 杂质模型一体项的目标作用电路：在 CNOT 奇偶框架内，由标签比特受控地在两个目标比特上施加 X 与 Z，实现所选的 Pauli 项（XX/YY 跃迁或格点相位）。 | 6 | 6 | 0 | 4 |
| `arxiv2610.03686_complementary_pair_cswap_network_n5_10.qasm` | [2610.03686v2](https://arxiv.org/abs/2610.03686v2) | Efficient Block Encoding of Structured Hamiltonians by Separating Where and What | N=5 的互补对置换网络：5 个由地址位异或奇偶性控制的 CSWAP 先定向互补对 {1,2},{3,4}，再经两棵交换树把所选位点对 (j,j′) 分别搬到 q0 和 q1。 | 10 | 10 | 5 | 9 |
| `arxiv2610.03686_cswap_swap_tree_10leaf_14.qasm` | [2610.03686v2](https://arxiv.org/abs/2610.03686v2) | Efficient Block Encoding of Structured Hamiltonians by Separating Where and What | 10 个叶子、4 位地址的受控交换树：9 个 CSWAP 按地址位逐层交换，把地址 a 选中的叶子比特内容搬到根（叶子 0），用于块编码 SELECT 的置换网络。 | 14 | 18 | 9 | 15 |
| `arxiv2610.01446_off_diagonal_ansatz_layer_n4_4.qasm` | [2610.01446v1](https://arxiv.org/abs/2610.01446v1) | Unflattening by Flattening -- How Input Distributions Shape Output Variance in Angle-Encoded Circuits | 4 比特非对角拟设的一层：在相邻比特对上依次施加 RXX 与 RYY 旋转（砖墙排列），李代数为 so(n)⊕so(n)，对计算基输入输出恒为零。 | 4 | 12 | 0 | 20 |
| `arxiv2610.01446_matchgate_ansatz_layer_n4_4.qasm` | [2610.01446v1](https://arxiv.org/abs/2610.01446v1) | Unflattening by Flattening -- How Input Distributions Shape Output Variance in Angle-Encoded Circuits | 4 比特匹配门（matchgate）拟设的一层：每个比特先做 RZ，再在相邻比特上施加砖墙式 RXX 旋转，其动力学李代数为 so(2n)。 | 4 | 6 | 0 | 11 |
| `arxiv2610.00579_shift_basis_unitary_3.qasm` | [2610.00579v1](https://arxiv.org/abs/2610.00579v1) | Characterizing unitaries via quasi-process functions | 在 3 个比特上实现 SHIFT 幺正：依次对 A、B、C 施加由另外两方（混合开/闭控制）控制的 Hadamard，将计算基映射为非纠缠量子非定域（QNLWE）的 SHIFT 积态基。 | 3 | 0 | 3 | 17 |
| `arxiv2610.00547_faq_running_example_c3_3.qasm` | [2610.00547v1](https://arxiv.org/abs/2610.00547v1) | Unifying and Extending Strong Simulation of Quantum Circuits | 强模拟论文中张量压缩一节的 3 比特运行示例线路 C_3：依次施加 H 层、T 层、全对 CZ 层、H 层、全对 CZ 层和 H 层，用于展示分隔符对称性与相位系数张量压缩。 | 3 | 6 | 0 | 10 |
| `arxiv2609.21153_periodic_shift_increment_4q_4.qasm` | [2609.21153v1](https://arxiv.org/abs/2609.21153v1) | Shock-Capturing Quantum Algorithm for the Linear Advection Operator | 在 4 个数据比特上实现周期性平移算符 U⁺（\|j⟩→\|j+1 mod 16⟩）的线路：由控制数依次递减的多控 NOT 级联（C³X、C²X、CX、X）构成，用作迎风格式平流 LCU 算法中的选择算符。 | 4 | 15 | 1 | 29 |
| `arxiv2609.16721_d2q5_sbm_amplitude_encoding_3.qasm` | [2609.16721v1](https://arxiv.org/abs/2609.16721v1) | Rotation Collision based Quantum Lattice Boltzmann Methods | D2Q5 格子玻尔兹曼模型的三比特 Shende–Bullock–Markov 振幅编码线路：用逐级（开/闭）受控 R_y 旋转把 5 个非负振幅写入 \|000>…\|100>，零填充分支省略。 | 3 | 18 | 0 | 32 |
| `arxiv2609.08233_global_cz_16_16.qasm` | [2609.08233v1](https://arxiv.org/abs/2609.08233v1) | Transversal Fanout for Fault Tolerant Distributed Quantum Computing: Analysis and Application | 在 4 个节点共 16 个比特上实现全局受控 Z 门 GCZ₁₆：对所有 120 对比特两两施加 CZ，作为分布式扇出（fanout）实现的目标运算。 | 16 | 120 | 0 | 29 |
| `arxiv2609.06179_d2q4_lgca_collision_5.qasm` | [2609.06179v1](https://arxiv.org/abs/2609.06179v1) | Quantum lattice Boltzmann method via density-matrix encoding for fluid simulation with wall boundary conditions | D2Q4 格子气碰撞步线路：借助一个辅助比特，用 CNOT 与 Toffoli 交换速度占据态 \|0101> 与 \|1010>，其余基态不变，辅助比特还原为 \|0>。 | 5 | 6 | 5 | 9 |
| `arxiv2609.03583_qft5_parity_twine_linear_dcnot_5.qasm` | [2609.03583v1](https://arxiv.org/abs/2609.03583v1) | Optimizing Atom Transport, Gate-Count and Depth with Parity Twine | 在 5 比特线性近邻阵列上用 Parity Twine 网络实现的量子傅里叶变换 QFT₅：由逐级缩短的 DCNOT 链传播奇偶标签并穿插 R_Z/R_X 旋转，最后用 4 个 CNOT 解码恢复各比特标签。 | 5 | 24 | 0 | 23 |
| `arxiv2609.01904_incrementer_shift_3q_3.qasm` | [2609.01904v1](https://arxiv.org/abs/2609.01904v1) | Quantum Circuit and Tensor Network Implementation of the 2D Acoustic Wave Equation | 在 3 个比特上实现循环移位算符 S⁺ 的增量线路：依次用 Toffoli、CNOT 和 X 从最高位到最低位实现 \|x⟩→\|x+1 mod 8⟩，用于声波方程有限差分格式中的离散拉普拉斯算符。 | 3 | 1 | 1 | 3 |
| `arxiv2608.20443_quantum_switch_fredkin_wiring_6.qasm` | [2608.20443v3](https://arxiv.org/abs/2608.20443v3) | Granthi: Higher-Order Quantum Programming via Unitary Wiring | Granthi 编译器为相干量子开关生成的 6 比特布线线路：以 q4 上的布尔标签为控制，用 4 个 Fredkin 门把载荷 q5 按 b=0 时先 g 后 f、b=1 时先 f 后 g 的顺序接入 f、g 的边界线。 | 6 | 8 | 4 | 9 |
| `arxiv2608.17136_coin_controlled_increment_3q_4.qasm` | [2608.17136v2](https://arxiv.org/abs/2608.17136v2) | Gate-level Implementation and Resource Analysis of Lackadaisical Quantum Walk Search | 在 3 比特位置寄存器上实现由硬币比特控制的循环加一（移位算符 S+）：硬币为 \|1> 时依次用 C³X、C²X、CX 将位置 x 映射到 x+1 mod 8。 | 4 | 15 | 1 | 28 |
| `arxiv2608.11733_double_excitation_12cx_depth7_relabel_4.qasm` | [2608.11733v3](https://arxiv.org/abs/2608.11733v3) | A 12-CNOT Double Qubit Excitation Gate | 本文提出的 CNOT 深度 7 的 12-CNOT 双激发门变体，输出比特按 (q_i,q_j,q_k,q_l)→(q_k,q_l,q_i,q_j) 重新标记。 | 4 | 12 | 0 | 17 |
| `arxiv2608.11733_double_excitation_12cx_4.qasm` | [2608.11733v3](https://arxiv.org/abs/2608.11733v3) | A 12-CNOT Double Qubit Excitation Gate | 本文提出的 12-CNOT 双量子比特激发门分解（CNOT 深度 8），在 \|0011⟩ 与 \|1100⟩ 之间实现角度 θ 的 Givens 旋转。 | 4 | 12 | 0 | 17 |
| `arxiv2608.11733_double_excitation_c3ry_4.qasm` | [2608.11733v3](https://arxiv.org/abs/2608.11733v3) | A 12-CNOT Double Qubit Excitation Gate | 双量子比特激发算符的高层实现：先用 3 个 CNOT 做基变换，再施加以 q_j,q_k,q_l 为控制、作用在 q_i 上的三控 R_y(2θ) 旋转，最后用镜像 CNOT 还原，实现 \|0011⟩ 与 \|1100⟩ 之间的转动。 | 4 | 26 | 0 | 32 |
| `arxiv2608.09578_highest_bit_const_adder_uncompute_6.qasm` | [2608.09578v2](https://arxiv.org/abs/2608.09578v2) | Quantum Uncomputation of Clean and Dirty Ancilla Qubits | 由自动反计算编译得到的 HighestBitConstAdder 线路：用 2 个脏辅助比特 a₀,a₁ 计算 x₃ ← x₃⊕x₂⊕x₀x₁⊕x₀x₁x₂，随后的 Toffoli/CNOT 序列把脏辅助比特恢复为原值。 | 6 | 5 | 6 | 11 |
| `arxiv2608.09578_highest_bit_const_adder_dirty_7.qasm` | [2608.09578v2](https://arxiv.org/abs/2608.09578v2) | Quantum Uncomputation of Clean and Dirty Ancilla Qubits | 使用 3 个脏辅助比特 a₀,a₁,a₂ 计算 4 比特整数 x 加常数 (1010)₂（x₀ 为最低位）后的最高位并写入 x₃ 的线路（无反计算）：x₃ ← x₃⊕x₂⊕x₀x₁⊕x₀x₁x₂。 | 7 | 4 | 4 | 9 |
| `arxiv2608.09578_mch_dirty_ancilla_9.qasm` | [2608.09578v2](https://arxiv.org/abs/2608.09578v2) | Quantum Uncomputation of Clean and Dirty Ancilla Qubits | 用 2 个脏辅助比特 a₀、a₂ 和 1 个干净辅助比特 a₁ 实现的 5 控制 H 门（MCH）线路：由 Toffoli 级联把 A∧B∧C 写入 a₁，再用两次受控受控 H（CCH）与 Toffoli 夹逼使 T 上仅当 A∧B∧C∧D∧E 时作用 H（不做反计算）。 | 9 | 0 | 6 | 14 |
| `arxiv2608.09509_three_photon_bs_unit_gray_4.qasm` | [2608.09509v1](https://arxiv.org/abs/2608.09509v1) | Gate-based emulation of boson sampling using photonic qubits | 在 4 个比特（两个模式各用 2 比特 Gray 码表示 0–3 个光子）上实现三光子玻色采样中单个 50:50 分束器的重复单元：先把 Gray 码转换为按光子数分区的编码，施加含 Z、R_y(2π/3)、受控 H 的分束器变换，再转换回 Gray 码。 | 4 | 5 | 19 | 46 |
| `arxiv2608.09509_boson_sampling_optimized_1010_4.qasm` | [2608.09509v1](https://arxiv.org/abs/2608.09509v1) | Gate-based emulation of boson sampling using photonic qubits | 在 4 个比特（3 个路径比特 + 1 个偏振比特）上实现针对输入 \|1010> 的四模式两光子干涉仪简化线路：通过 X、H、CNOT、Toffoli 与受控 H 门直接产生对应的玻色采样输出分布。 | 4 | 4 | 1 | 13 |
| `arxiv2608.09509_boson_sampling_4mode_2photon_5.qasm` | [2608.09509v1](https://arxiv.org/abs/2608.09509v1) | Gate-based emulation of boson sampling using photonic qubits | 在 5 个比特（4 个模式比特 + 1 个辅助比特）上模拟两光子四模式玻色采样干涉仪（分束器 B12、B34 后接 B23）：每个分束器由反控 Toffoli 识别旁观模式为空后、在两模式比特上施加编码的两光子分束器单元，再反算辅助比特。 | 5 | 9 | 12 | 57 |
| `arxiv2608.06570_qlb_streaming_increment_3bit_3.qasm` | [2608.06570v2](https://arxiv.org/abs/2608.06570v2) | Exact quantum circuits for a lattice Boltzmann realization of the Dirac equation | 格点玻尔兹曼 Dirac 方案中的流动（平移）算子：在 3 比特位置寄存器上用多控 X 级联实现 \|x⟩→\|x+1 mod 8⟩（p0 为最低位）。 | 3 | 1 | 1 | 3 |
| `arxiv2608.03962_poor_mans_cat_parity_sampler_9.qasm` | [2608.03962v1](https://arxiv.org/abs/2608.03962v1) | Separating quantum circuits from classical LLMs | 在 5 个系统比特与 4 个辅助比特上的常深度 QNC⁰ 采样线路：H 后用两层 CNOT 将相邻 Z_iZ_{i+1} 宇称写入辅助比特（测量得到穷人猫态），再对系统比特施加 H 并测量，输出为偶宇称均匀分布 U_5^⊕。 | 9 | 8 | 0 | 4 |
| `arxiv2607.28499_wave2d_bright_flux_rotation_Rx_5.qasm` | [2607.28499v2](https://arxiv.org/abs/2607.28499v2) | Structure-Preserving Quantum Simulation of Wave Equations on a Trapped-Ion Processor | 二维声波方程电路中的亮-通量旋转 ℛ_x：以幅值位为控制的单控与双控 R_X 门在场比特 f1 上合成模式相关的角度 β_k=2tΩ_k。 | 5 | 36 | 0 | 72 |
| `arxiv2607.28499_wave2d_givens_transform_G_6.qasm` | [2607.28499v2](https://arxiv.org/abs/2607.28499v2) | Structure-Preserving Quantum Simulation of Wave Equations on a Trapped-Ion Processor | 二维声波方程电路中的 Givens 变换 𝒢：在 f1=0 条件下，用由幅值位控制的（双）控 R_Y 旋转合成与模式相关的角度 α_k，把两个速度分量旋转到亮-暗基。 | 6 | 96 | 0 | 136 |
| `arxiv2607.28499_wave2d_phase_transform_P_8.qasm` | [2607.28499v2](https://arxiv.org/abs/2607.28499v2) | Structure-Preserving Quantum Simulation of Wave Equations on a Trapped-Ion Processor | 二维声波方程傅里叶块电路中的相位变换 𝒫：以场比特 f0,f1 选择 x/y 分量，用由符号位与幅值位控制的多控相位门合成保留模式 k∈{0,±1,±2} 的相位 φ_k。 | 8 | 96 | 0 | 166 |
| `arxiv2607.27915_mvc_constrained_walk_4vertex_4.qasm` | [2607.27915v1](https://arxiv.org/abs/2607.27915v1) | Iterative quantum algorithms for the minimum vertex cover problem based on continuous-time quantum walks | 最小顶点覆盖约束量子游走的 p=1 线路（4 顶点示例图）：先用 X 门制备全覆盖态 \|1111⟩，再按顶点顺序施加以其全部邻居为控制的多控 RX 旋转，使振幅只在可行顶点覆盖子空间内传播。 | 4 | 56 | 0 | 89 |
| `arxiv2607.27247_harmonic_frame_povm_naimark_3.qasm` | [2607.27247v1](https://arxiv.org/abs/2607.27247v1) | Designing tight frames for quantum computing | 用 2 个辅助比特通过 Naimark 扩张实现单比特 C_4 调和紧框架 POVM E_k 的线路：先作置换 P_σ=CNOT(ρ→a₁)，再对 3 比特施加量子傅里叶变换 F_8（H、受控 S/T 与 SWAP），测量辅助比特得到 k=2i+j。 | 3 | 7 | 0 | 13 |
| `arxiv2607.20943_vqc_ry_rz_cz_full_4.qasm` | [2607.20943v1](https://arxiv.org/abs/2607.20943v1) | An Analytically Trained Variational Surrogate for Quantum Phase Estimation on NISQ Hardware | 在 4 个比特上构造 QPE 替代用变分量子线路（p=1 层）：每个比特施加 R_Y、R_Z 旋转，随后在所有 6 对比特间施加 CZ（全连接纠缠层），最后再施加一层 R_Y、R_Z 旋转。 | 4 | 6 | 0 | 9 |
| `arxiv2607.16800_hea_ryrzrx_cnot_ring_n4_d2_4.qasm` | [2607.16800v2](https://arxiv.org/abs/2607.16800v2) | Identity-Paired Progressive Depth Training: When Trainability Persists Beyond Expressibility | 4 比特、2 层的标准硬件高效拟设（HEA）：每层先对每个比特施加 R_Y、R_Z、R_X 三个参数化旋转，再施加 1→2→3→4→1 的环形 CNOT 纠缠层。 | 4 | 8 | 0 | 14 |
| `arxiv2607.11665_index_transposition_v3_4.qasm` | [2607.11665v1](https://arxiv.org/abs/2607.11665v1) | The Time-Space Complexity of Checking Multiple Assertions in Quantum Programs | 在 4 个比特（1 个 fail 标志 + 3 比特索引寄存器）上实现断言检查中的受控换位 V³_Tran：沿 Gray 路径用三个多控非门（G1 G2 G1 回文序列），在 fail=1 时交换索引态 \|000> 与 \|011>，其余基态保持不变。 | 4 | 42 | 0 | 80 |
| `arxiv2607.09976_vqe_style_diagnostic_kernel_4.qasm` | [2607.09976v1](https://arxiv.org/abs/2607.09976v1) | GPU-Accelerated Host-Aware Dead-Measurement Detection in Hybrid Quantum--Classical Programs: Full Version | 论文的 VQE 型诊断工作负载量子核：4 比特上先用 3 个 Toffoli 构成固定纠缠骨架，再施加 R_z/R_y 单比特旋转层（角度 0 或 π/4），最后用 CZ、CNOT 与 Toffoli 组成关联层。 | 4 | 2 | 4 | 7 |
| `arxiv2607.06230_full_entangler_pqc_layer_4.qasm` | [2607.06230v1](https://arxiv.org/abs/2607.06230v1) | Entanglement as a Structural Complexity Axis: A PAC-Bayesian View of Generalization in Quantum Policies and Value Functions | 4 比特参数化量子线路的一层（全连接版本）：先用 R_Y(x_i) 角度编码输入，再对每个比特施加可训练的 R_Y、R_Z，随后施加全部 6 个两两 CNOT（全对全纠缠块），最后读出 ⟨Z_0⟩。 | 4 | 6 | 0 | 8 |
| `arxiv2607.01180_cz02_routed_transpiled_3.qasm` | [2607.01180v1](https://arxiv.org/abs/2607.01180v1) | Non-Clifford Benchmarking via Ensemble Feature Selection | 在 3 个比特线性拓扑上实现经由中间路由比特 q1 的 CZ(0,2)：由 12 个 √X 与 7 个原生 CZ 组成（深度 13）的转译线路，用作 EFS 估计器的 Clifford 验证基准。 | 3 | 7 | 0 | 13 |
<!-- circuits-table:end -->
