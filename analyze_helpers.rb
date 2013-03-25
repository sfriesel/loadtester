def show_stats(d, prefix="")
  n = d.size
  puts "#{ prefix }number of entries: #{ n } #"

  avg = d.reduce(:+) / n
  puts "#{ prefix }average: #{ avg } s"

  med = d[n / 2]
  puts "#{ prefix }median: #{ med } s"

  std_dev = (d.reduce(0) { |acc, e| acc + (e - avg) ** 2 } / n) ** 0.5
  puts "#{ prefix }standard deviation: #{ std_dev }"
end
