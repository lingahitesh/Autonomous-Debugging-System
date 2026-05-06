public class Calculator
{
    public int compute(int n)
    {
        utils helper = new utils();
        int sum = helper.sumToN(n);
        int avg = helper.average(sum, n);
        return avg;
    }
}